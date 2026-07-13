import json
import logging
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from app.ai_service import generate_text

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 15
CACHE_TTL_SECONDS = 300

_url_cache: dict[str, tuple[float, dict]] = {}


def _get_cache_key(url: str) -> str:
    return url.strip().lower().rstrip("/")


def _cached_result(url: str) -> Optional[dict]:
    key = _get_cache_key(url)
    entry = _url_cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _set_cache(url: str, data: dict):
    key = _get_cache_key(url)
    _url_cache[key] = (time.time(), data)


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|careers|boards|job)\.", "", domain)
    domain = domain.split(".")[0] if domain.count(".") > 1 else domain
    patterns = {
        "linkedin": r"linkedin\.com",
        "indeed": r"indeed\.com",
        "greenhouse": r"greenhouse\.io",
        "lever": r"lever\.co",
        "ashby": r"ashbyhq\.com",
        "workday": r"myworkdayjobs\.com|wd5\.myworkdayjobs|workday\.com",
        "wellfound": r"wellfound\.com|angel\.co",
        "ycombinator": r"ycombinator\.com\/jobs",
        "naukri": r"naukri\.com",
        "internshala": r"internshala\.com",
        "glassdoor": r"glassdoor\.com",
        "monster": r"monster\.com",
        "ziprecruiter": r"ziprecruiter\.com",
        "simplyhired": r"simplyhired\.com",
        "stackoverflow": r"stackoverflow\.com\/jobs",
        "google_careers": r"careers\.google\.com",
        "microsoft_careers": r"careers\.microsoft\.com",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, url.lower()):
            return name
    return "unknown"


def fetch_page(url: str) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            results.append(data)
            if isinstance(data, dict) and data.get("@graph"):
                results.extend(data["@graph"])
            if isinstance(data, list):
                results.extend(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def find_job_posting_ld(ld_items: list[dict]) -> Optional[dict]:
    for item in ld_items:
        if isinstance(item, dict):
            context = item.get("@context", "")
            type_ = item.get("@type", "")
            if "schema.org" in str(context) or "JobPosting" in str(type_):
                if type_ == "JobPosting" or (
                    isinstance(type_, list) and "JobPosting" in type_
                ):
                    return item
    return None


def extract_meta_tags(soup: BeautifulSoup) -> dict:
    meta = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property", "") or tag.get("name", "")
        content = tag.get("content", "")
        if prop and content:
            meta[prop.strip()] = content.strip()
    return meta


def _text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _attr(soup: BeautifulSoup, selector: str, attr: str = "content") -> str:
    el = soup.select_one(selector)
    return el.get(attr, "").strip() if el else ""


def parse_linkedin(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1.topcard__title, h1.job-title")
    if title:
        result["title"] = title
    company = _text(soup, "a.topcard__org-name-link, span.topcard__flavor")
    if company:
        result["company_name"] = company
    loc = _text(
        soup, "span.topcard__flavor--bullet, span.job-header-info__location"
    )
    if loc:
        result["location"] = loc
    desc = _text(soup, "div.description__text, section.core-section-container")
    if desc:
        result["description"] = desc
    criteria_items = soup.select("li.job-criteria__item")
    for item in criteria_items:
        label = _text(item, "h3.job-criteria__subheader")
        value = _text(item, "span.job-criteria__text")
        if "seniority" in label.lower() or "experience" in label.lower():
            result["experience_required"] = value
        elif "employment" in label.lower():
            result["employment_type"] = value
        elif "function" in label.lower():
            pass
    return result


def parse_indeed(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1.jobsearch-JobInfoHeader-title")
    if title:
        result["title"] = title
    company = _text(soup, "div[data-company-name]")
    if not company:
        company = _text(soup, "div.jobsearch-CompanyReview--heading")
    if company:
        result["company_name"] = company
    loc = _text(soup, "div.jobsearch-JobInfoHeader-subtitle")
    if loc:
        loc = re.split(r"[-|]", loc)[0].strip()
        result["location"] = loc
    desc = _text(soup, "div.jobsearch-jobDescriptionText")
    if desc:
        result["description"] = desc
    salary = _text(soup, "span#salaryText, div.salaryText")
    if salary:
        result["salary"] = salary.strip()
    return result


def parse_greenhouse(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1[class*=title], h1.app-title")
    if title:
        result["title"] = title
    company = _text(soup, "span.company-name")
    if not company:
        company = _text(soup, "a.logo-link")
    if company:
        result["company_name"] = company
    loc = _text(soup, "div.location")
    if loc:
        result["location"] = loc
    desc = _text(soup, "div.job-description")
    if desc:
        result["description"] = desc
    meta_items = soup.select("div.job-meta span")
    for span in meta_items:
        text = span.get_text(strip=True)
        if text and not result.get("employment_type"):
            types = {"full-time", "part-time", "contract", "internship", "temporary"}
            if text.lower().replace(" ", "-") in types:
                result["employment_type"] = text
    return result


def parse_lever(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1[class*=title]")
    if title:
        result["title"] = title
    company = _text(soup, "div.logo-name, span.company-name")
    if company:
        result["company_name"] = company
    loc = _text(soup, "div.location, span.sort-by-location")
    if loc:
        result["location"] = loc
    desc = _text(soup, "div.content, div.posting")
    if desc:
        result["description"] = desc
    return result


def parse_workday(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1[data-automation-id*=title], h1.job-title")
    if title:
        result["title"] = title
    company = _text(soup, "div[data-automation-id*=company]")
    if company:
        result["company_name"] = company
    loc = _text(soup, "div[data-automation-id*=location]")
    if loc:
        result["location"] = loc
    desc = _text(soup, "div[data-automation-id*=description]")
    if desc:
        result["description"] = desc
    return result


def parse_naukri(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1[class*=title]")
    if title:
        result["title"] = title
    company = _text(soup, "a[class*=companyLink]")
    if company:
        result["company_name"] = company
    exp = _text(soup, "span[class*=exp]")
    if exp:
        result["experience_required"] = exp
    salary = _text(soup, "span[class*=salary]")
    if salary:
        result["salary"] = salary
    loc = _text(soup, "span[class*=location]")
    if loc:
        result["location"] = loc
    desc = _text(soup, "div[class*=description]")
    if desc:
        result["description"] = desc
    return result


def parse_internshala(soup: BeautifulSoup, url: str) -> dict:
    result = {}
    title = _text(soup, "h1[class*=heading], h1.internship-title")
    if title:
        result["title"] = title
    company = _text(soup, "h4[class*=company]")
    if company:
        result["company_name"] = company
    loc = _text(soup, "span[class*=location]")
    if loc:
        result["location"] = loc
    stipend = _text(soup, "span[class*=stipend]")
    if stipend:
        result["salary"] = stipend
    desc = _text(soup, "div[class*=description]")
    if desc:
        result["description"] = desc
    return result


_PLATFORM_PARSERS = {
    "linkedin": parse_linkedin,
    "indeed": parse_indeed,
    "greenhouse": parse_greenhouse,
    "lever": parse_lever,
    "workday": parse_workday,
    "naukri": parse_naukri,
    "internshala": parse_internshala,
}


def from_jsonld(ld_items: list[dict]) -> dict:
    posting = find_job_posting_ld(ld_items)
    if not posting:
        return {}
    result = {}
    result["title"] = posting.get("title", "")
    result["description"] = posting.get("description", "")
    hiring_org = posting.get("hiringOrganization", {})
    if isinstance(hiring_org, dict):
        result["company_name"] = hiring_org.get("name", "")
        result["company_logo"] = hiring_org.get("logo", "")
    result["location"] = ""
    loc = posting.get("jobLocation", {})
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            parts = [addr.get(k, "") for k in ("addressLocality", "addressRegion", "addressCountry")]
            result["location"] = ", ".join(p for p in parts if p)
        else:
            result["location"] = loc.get("address", "")
    elif isinstance(loc, str):
        result["location"] = loc
    if isinstance(loc, list):
        addresses = []
        for l in loc:
            addr = l.get("address", {}) if isinstance(l, dict) else {}
            if isinstance(addr, dict):
                parts = [addr.get(k, "") for k in ("addressLocality", "addressRegion", "addressCountry")]
                addresses.append(", ".join(p for p in parts if p))
        result["location"] = "; ".join(addresses)
    result["salary"] = ""
    salary_obj = posting.get("baseSalary", {})
    if isinstance(salary_obj, dict):
        value = salary_obj.get("value", {})
        if isinstance(value, dict):
            result["salary_min"] = value.get("minValue")
            result["salary_max"] = value.get("maxValue")
            result["currency"] = salary_obj.get("currency", "")
            result["salary_period"] = salary_obj.get("@type", "")
    result["employment_type"] = posting.get("employmentType", "")
    if isinstance(result["employment_type"], list):
        result["employment_type"] = ", ".join(result["employment_type"])
    result["experience_required"] = posting.get("experienceRequirements", {}).get(
        "name", ""
    ) if isinstance(posting.get("experienceRequirements"), dict) else ""
    result["skills"] = posting.get("skills", [])
    if isinstance(result["skills"], str):
        result["skills"] = [s.strip() for s in result["skills"].split(",")]
    posted = posting.get("datePosted", "")
    if posted:
        result["date_posted"] = posted
    valid_through = posting.get("validThrough", "")
    if valid_through:
        result["expiry_date"] = valid_through
    result["url"] = posting.get("url", "")
    return result


def from_meta(meta: dict, url: str) -> dict:
    result = {}
    title = meta.get("og:title", meta.get("twitter:title", ""))
    if title:
        result["title"] = title
    description = meta.get("og:description", meta.get("twitter:description", ""))
    if description:
        result["description"] = description
    image = meta.get("og:image", meta.get("twitter:image", ""))
    if image:
        result["company_logo"] = image
    return result


def from_llm_fallback(page_text: str, url: str) -> dict:
    try:
        system_instruction = (
            "You are a job posting parser. Extract structured information from the "
            "raw HTML text provided. Return ONLY valid JSON (no markdown, no "
            "explanations) matching this schema: "
            '{"title":"","company_name":"","company_logo":"","location":"",'
            '"salary":"","employment_type":"","experience_required":"",'
            '"description":"","requirements":[],"responsibilities":[],'
            '"skills":[],"url":"' + url.replace('"', '\\"') + '"}'
        )
        prompt = (
            f"Extract job posting details from this page text. "
            f"Return ONLY valid JSON:\n\n{page_text[:12000]}"
        )
        raw = generate_text(prompt, system_instruction=system_instruction)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning("LLM fallback parsing failed: %s", e)
        return {}


def clean_html_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


TECH_STACK_REGEX = re.compile(
    r"\b(Python|Flask|Django|FastAPI|JavaScript|TypeScript|React|Next[.\s]*[Jj][Ss]|"
    r"Vue|Angular|Svelte|Node|Java|Kotlin|Go|Golang|Rust|C\+\+|C#|CSharp|"
    r"[.]NET|PHP|Ruby|Swift|SQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|"
    r"Docker|Kubernetes|K8s|Terraform|AWS|GCP|Azure|GraphQL|gRPC|REST|"
    r"Kafka|RabbitMQ|PyTorch|TensorFlow|Scikit-learn|Pandas|NumPy|"
    r"Git|Jenkins|CI/CD|Linux|Bash|Nginx|Apache|DynamoDB|Cassandra|Firebase|Supabase|"
    r"Flutter|Dart|Selenium|Cypress|Playwright|Jest|Pytest)\b"
)


def extract_tech_stack(text: str) -> list[str]:
    found = TECH_STACK_REGEX.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for skill in found:
        normalized = skill.replace(".", "").replace(" ", "").lower()
        canonical = {
            "golang": "Go",
            "nextjs": "Next.js",
            "next": "Next.js",
            "csharp": "C#",
            "dotnet": ".NET",
            "k8s": "Kubernetes",
            "reactjs": "React",
            "vuejs": "Vue.js",
            "nodejs": "Node.js",
            "typescript": "TypeScript",
            "javascript": "JavaScript",
            "python": "Python",
            "flask": "Flask",
        }
        display = canonical.get(normalized, skill)
        if display not in seen:
            seen.add(display)
            result.append(display)
    return result


def parse_job_url(url: str) -> dict:
    cached = _cached_result(url)
    if cached:
        return dict(cached)

    html = fetch_page(url)
    if not html:
        return {"url": url, "error": "Failed to fetch page"}

    soup = BeautifulSoup(html, "lxml")

    meta = extract_meta_tags(soup)
    ld_items = extract_json_ld(soup)

    result: dict = {"url": url, "source": url}

    jsonld_data = from_jsonld(ld_items)
    meta_data = from_meta(meta, url)
    platform = detect_platform(url)
    platform_parser = _PLATFORM_PARSERS.get(platform)
    platform_data = platform_parser(soup, url) if platform_parser else {}

    ordered_fields = [
        "title",
        "company_name",
        "company_logo",
        "location",
        "salary",
        "salary_min",
        "salary_max",
        "currency",
        "salary_period",
        "employment_type",
        "experience_required",
        "description",
        "requirements",
        "responsibilities",
        "skills",
        "date_posted",
        "expiry_date",
    ]

    for field in ordered_fields:
        val = (
            platform_data.get(field)
            or jsonld_data.get(field)
            or meta_data.get(field)
            or ""
        )
        if val:
            result[field] = val

    result["platform"] = platform

    if platform != "unknown":
        result["provider"] = platform

    description = result.get("description", "")
    if description and not result.get("skills"):
        result["skills"] = extract_tech_stack(description)

    if not result.get("requirements") and description:
        lines = [
            line.strip()
            for line in description.split("\n")
            if line.strip()
            and any(
                kw in line.lower()
                for kw in [
                    "requirement",
                    "qualification",
                    "preferred",
                    "must have",
                    "minimum",
                ]
            )
        ]
        if lines:
            result["requirements"] = lines

    if not result.get("responsibilities") and description:
        lines = [
            line.strip()
            for line in description.split("\n")
            if line.strip()
            and any(
                kw in line.lower()
                for kw in [
                    "responsibilit",
                    "what you",
                    "role",
                    "key accountabilit",
                    "you will",
                    "duties",
                    "day-to-day",
                ]
            )
        ]
        if lines:
            result["responsibilities"] = lines

    has_good_data = bool(
        result.get("title") and result.get("company_name") and result.get("description")
    )

    if not has_good_data:
        page_text = clean_html_text(soup)
        llm_data = from_llm_fallback(page_text, url)
        for field in ordered_fields:
            if not result.get(field) and llm_data.get(field):
                result[field] = llm_data[field]

    result["url"] = url
    result["source"] = url

    _set_cache(url, result)
    return result
