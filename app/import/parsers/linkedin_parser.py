import logging
import re
from .base import BaseParser

logger = logging.getLogger(__name__)

LINKEDIN_SECTION_MAP = {
    "experience": re.compile(
        r"\b(EXPERIENCE|WORK\s*HISTORY|EMPLOYMENT)\b", re.IGNORECASE
    ),
    "education": re.compile(r"\bEDUCATION\b", re.IGNORECASE),
    "skills": re.compile(r"\b(SKILLS|TOP\s*SKILLS)\b", re.IGNORECASE),
    "projects": re.compile(r"\bPROJECTS?\b", re.IGNORECASE),
    "certifications": re.compile(r"\b(CERTIFICATIONS?|LICENSES?)\b", re.IGNORECASE),
    "languages": re.compile(r"\bLANGUAGES?\b", re.IGNORECASE),
    "summary": re.compile(r"\b(ABOUT|SUMMARY)\b", re.IGNORECASE),
}


def _split_sections(text):
    lines = text.split("\n")
    sections = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        matched = None
        for name, pattern in LINKEDIN_SECTION_MAP.items():
            if pattern.search(stripped):
                matched = name
                break
        if matched:
            current_section = matched
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(stripped)

    logger.debug("Split %d lines into %d sections: %s", len(lines), len(sections), list(sections.keys()))
    return sections


LOCATION_PATTERNS = [
    re.compile(r"\b(area|greater|remote|united states|united kingdom)\b", re.IGNORECASE),
    re.compile(r",\s*(usa|uk|india|germany|canada|australia|france|spain|netherlands|singapore|japan|uae)\b", re.IGNORECASE),
    re.compile(r"^(san\s|new\s|los\s|las\s|hong\s)", re.IGNORECASE),
    re.compile(r"\b(bay area|silicon valley)\b", re.IGNORECASE),
]


def _parse_name_email_from_header(lines):
    info = {}
    for line in lines:
        if not line:
            continue
        lower = line.lower()

        if re.search(r"@", line) and not info.get("email"):
            info["email"] = line.strip()
            logger.debug("Parsed email: %s", info["email"])
            continue

        if re.search(r"linkedin\.com", lower) and not info.get("linkedin"):
            info["linkedin"] = line.strip()
            logger.debug("Parsed linkedin: %s", info["linkedin"])
            continue

        if re.search(r"\+?\d[\d\s\-\(\)]{7,}", line) and not info.get("phone"):
            info["phone"] = line.strip()
            logger.debug("Parsed phone: %s", info["phone"])
            continue

        if not info.get("full_name") and len(line.split()) in (2, 3) and not re.search(r"[@http]", lower):
            info["full_name"] = line.strip()
            logger.debug("Parsed full_name: %s", info["full_name"])
            continue

        if not info.get("title") and re.search(r"\bat\b", lower) and not re.search(r"[@http]", lower):
            info["title"] = line.strip()
            logger.debug("Parsed title (at-pattern): %s", info["title"])
            continue

        if not info.get("location"):
            for pat in LOCATION_PATTERNS:
                if pat.search(lower):
                    info["location"] = line.strip()
                    logger.debug("Parsed location: %s", info["location"])
                    break
            if info.get("location"):
                continue

        if not info.get("title") and not re.search(r"[@http]", lower):
            words = line.split()
            if len(words) >= 3:
                info["title"] = line.strip()
                logger.debug("Parsed title (fallback): %s", info["title"])

    return info


def _parse_experience(lines):
    entries = []
    current = {}
    bullet_mode = False
    for line in lines:
        if not line:
            if current:
                entries.append(current)
                current = {}
                bullet_mode = False
            continue

        if line.startswith("-") or line.startswith("•"):
            bullet_mode = True
            current.setdefault("bullets", []).append(line.lstrip("- •").strip())
            continue

        if re.match(r"\d{4}\s*[–—-]\s*(\d{4}|Present)", line, re.IGNORECASE):
            date_match = re.match(r"(\d{4})\s*[–—-]\s*(\d{4}|Present)", line, re.IGNORECASE)
            current["start"] = date_match.group(1)
            current["end"] = date_match.group(2)
            logger.debug("Parsed experience dates: %s - %s for role=%s", current.get("start"), current.get("end"), current.get("role"))
            bullet_mode = False
            continue

        if not current.get("role"):
            current["role"] = line.strip()
            logger.debug("Parsed experience role: %s", current["role"])
            bullet_mode = False
        elif not current.get("company"):
            current["company"] = line.strip()
            logger.debug("Parsed experience company: %s for role=%s", current["company"], current["role"])
            bullet_mode = False
        elif not bullet_mode:
            if not current.get("company"):
                current["company"] = line.strip()
            else:
                current.setdefault("bullets", []).append(line.strip())

    if current:
        entries.append(current)

    logger.debug("Parsed %d experience entries", len(entries))
    return entries


def _parse_education(lines):
    entries = []
    current = {}
    for line in lines:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        if not current.get("school"):
            current["school"] = line.strip()
        elif re.match(r"\d{4}\s*[–—-]\s*\d{4}", line):
            parts = re.split(r"\s*[–—-]\s*", line)
            current["start"] = parts[0].strip()
            current["end"] = parts[1].strip() if len(parts) > 1 else ""
        elif not current.get("degree") and not re.match(r"\d{4}", line):
            current["degree"] = line.strip()
    if current:
        entries.append(current)
    logger.debug("Parsed %d education entries", len(entries))
    return entries


def _parse_skills(lines):
    skills = []
    for line in lines:
        if not line:
            continue
        for item in re.split(r"[,\n•]", line):
            item = item.strip().lstrip("•- ")
            if item and len(item) > 1:
                skills.append(item)
    logger.debug("Parsed %d skills", len(skills))
    return skills


def _parse_projects(lines):
    entries = []
    current = {}
    for line in lines:
        if not line:
            if current and current.get("name"):
                entries.append(current)
                current = {}
            continue
        if not current.get("name"):
            current["name"] = line.strip()
        elif re.match(r"https?://", line):
            current["url"] = line.strip()
        else:
            current.setdefault("description", "")
            current["description"] += " " + line.strip()
    if current and current.get("name"):
        entries.append(current)
    logger.debug("Parsed %d project entries", len(entries))
    return entries


def _parse_certificates(lines):
    entries = []
    for line in lines:
        if not line:
            continue
        parts = re.split(r"\s*[–—-]\s*", line, maxsplit=1)
        entry = {"name": parts[0].strip()}
        if len(parts) > 1:
            entry["issuer"] = parts[1].strip()
        entries.append(entry)
    return entries


def _parse_languages(lines):
    entries = []
    for line in lines:
        if not line:
            continue
        parts = re.split(r"\s*[–—-]\s*", line, maxsplit=1)
        entry = {"name": parts[0].strip()}
        if len(parts) > 1:
            entry["level"] = parts[1].strip()
        entries.append(entry)
    return entries


class LinkedInParser(BaseParser):
    def parse(self, raw_data) -> dict:
        text = raw_data if isinstance(raw_data, str) else str(raw_data)
        result = self._empty_result()

        if not text.strip():
            logger.warning("Empty raw data provided to LinkedInParser")
            return result

        sections = _split_sections(text)
        logger.info("Parsing LinkedIn data with sections: %s", list(sections.keys()))

        for sec_name, sec_lines in sections.items():
            if sec_name == "header":
                info = _parse_name_email_from_header(sec_lines)
                result["personal_info"].update(info)
            elif sec_name == "summary":
                result["summary"] = " ".join(ln for ln in sec_lines if ln).strip()
            elif sec_name == "experience":
                result["experience"] = _parse_experience(sec_lines)
            elif sec_name == "education":
                result["education"] = _parse_education(sec_lines)
            elif sec_name == "skills":
                result["skills"] = _parse_skills(sec_lines)
            elif sec_name == "projects":
                result["projects"] = _parse_projects(sec_lines)
            elif sec_name == "certifications":
                result["certificates"] = _parse_certificates(sec_lines)
            elif sec_name == "languages":
                result["languages"] = _parse_languages(sec_lines)

        if not result["personal_info"].get("full_name"):
            for line in text.split("\n"):
                line = line.strip()
                if line and len(line.split()) in (2, 3) and not re.search(r"[@http]", line, re.IGNORECASE):
                    result["personal_info"]["full_name"] = line
                    logger.debug("Fallback name extraction: %s", line)
                    break

        logger.info(
            "LinkedIn parse complete: name=%s, email=%s, skills=%d, experience=%d, education=%d",
            result["personal_info"].get("full_name", "(none)"),
            result["personal_info"].get("email", "(none)"),
            len(result["skills"]),
            len(result["experience"]),
            len(result["education"]),
        )
        return result
