import re
import requests
from .base import BaseParser


class PortfolioParser(BaseParser):

    def parse(self, raw_data) -> dict:
        url = raw_data.strip() if isinstance(raw_data, str) else str(raw_data)
        result = self._empty_result()

        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "CareerOS/1.0"})
            resp.raise_for_status()
        except requests.RequestException:
            return result

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
        except ImportError:
            result["personal_info"]["website"] = url
            return result

        result["personal_info"]["website"] = url

        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()
            parts = re.split(r"\s*[|–—-]\s*", title_text)
            result["personal_info"]["full_name"] = parts[0].strip()

        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            result["summary"] = meta_desc["content"].strip()

        for tag in soup.find_all(["h1", "h2", "h3", "section", "article"]):
            text = tag.get_text(strip=True)
            lower = text.lower()

            if any(w in lower for w in ["skill", "tech", "tool", "language"]):
                parent = tag.find_parent() or tag
                result["skills"] = list(set(
                    s.strip() for s in re.split(r"[,\n•/]", parent.get_text())
                    if len(s.strip()) > 1 and not any(w in s.lower() for w in ["skill", "tech"])
                ))

            if any(w in lower for w in ["project", "portfolio", "work"]):
                project_items = []
                for item in tag.find_all(["li", "div", "p"]):
                    text_item = item.get_text(strip=True)
                    if text_item and len(text_item) > 5:
                        project_items.append({"name": text_item})
                if project_items:
                    result["projects"].extend(project_items)

            if any(w in lower for w in ["experience", "work", "employment"]):
                exp_items = []
                for item in tag.find_all(["li", "div", "p"]):
                    text_item = item.get_text(strip=True)
                    if text_item and len(text_item) > 5:
                        exp_items.append({"role": text_item})
                if exp_items:
                    result["experience"].extend(exp_items)

            if any(w in lower for w in ["education", "school", "university", "college"]):
                edu_items = []
                for item in tag.find_all(["li", "div", "p"]):
                    text_item = item.get_text(strip=True)
                    if text_item and len(text_item) > 5:
                        edu_items.append({"school": text_item})
                if edu_items:
                    result["education"].extend(edu_items)

        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            text = link.get_text(strip=True).lower()
            if "linkedin.com" in href and not result["personal_info"].get("linkedin"):
                result["personal_info"]["linkedin"] = href
            elif "github.com" in href and not result["personal_info"].get("github"):
                result["personal_info"]["github"] = href

        return result
