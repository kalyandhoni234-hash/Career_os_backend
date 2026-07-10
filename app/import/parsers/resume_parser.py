import re
from .base import BaseParser


SECTION_PATTERNS = {
    "experience": re.compile(
        r"\b(EXPERIENCE|WORK\s*HISTORY|EMPLOYMENT|PROFESSIONAL\s*EXPERIENCE)\b",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"\b(EDUCATION|ACADEMIC|SCHOOL|UNIVERSITY|COLLEGE)\b", re.IGNORECASE
    ),
    "skills": re.compile(
        r"\b(SKILLS|TECHNICAL\s*SKILLS|CORE\s*COMPETENCIES|EXPERTISE)\b", re.IGNORECASE
    ),
    "projects": re.compile(
        r"\b(PROJECTS|PORTFOLIO|PERSONAL\s*PROJECTS)\b", re.IGNORECASE
    ),
    "certificates": re.compile(
        r"\b(CERTIFICATIONS?|CERTIFICATES|LICENSES?|ACCREDITATIONS?)\b", re.IGNORECASE
    ),
    "achievements": re.compile(
        r"\b(ACHIEVEMENTS|AWARDS|HONORS|ACCOMPLISHMENTS)\b", re.IGNORECASE
    ),
    "languages": re.compile(r"\b(LANGUAGES|LANGUAGE\s*PROFICIENCY)\b", re.IGNORECASE),
    "publications": re.compile(
        r"\b(PUBLICATIONS|RESEARCH|PAPERS?|THESIS)\b", re.IGNORECASE
    ),
    "summary": re.compile(
        r"\b(SUMMARY|PROFILE|ABOUT\s*ME|OBJECTIVE|PROFESSIONAL\s*SUMMARY)\b",
        re.IGNORECASE,
    ),
}


NAME_EMAIL_PHONE = re.compile(
    r"(?P<email>[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})|"
    r"(?P<phone>[\+]?[\d\-\(\)\s]{7,20})",
    re.IGNORECASE,
)


def _guess_name(text):
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    if not lines:
        return ""
    first = lines[0]
    if len(first.split()) in (2, 3) and not re.search(r"[@http]", first, re.IGNORECASE):
        return first
    return ""


def _split_sections(text):
    lines = text.split("\n")
    sections = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        matched = None
        for name, pattern in SECTION_PATTERNS.items():
            if pattern.search(stripped):
                matched = name
                break
        if matched:
            current_section = matched
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(stripped)

    return sections


def _parse_experience(lines):
    entries = []
    current = {}
    for line in lines:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        line_lower = line.lower()
        if (
            any(w in line_lower for w in ["- bullet", "•", "- "])
            or line.startswith("-")
            or line.startswith("•")
        ):
            current.setdefault("bullets", []).append(line.lstrip("- •").strip())
        elif re.match(r".+\s*[–—-]\s*.+", line) and not re.search(r"@", line):
            current.setdefault("bullets", []).append(line.strip())
        else:
            if current and current.get("role"):
                entries.append(current)
                current = {}
            current["role"] = line.strip()
    if current:
        entries.append(current)
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
        current.setdefault("school", line.strip())
        if re.match(r".+\s*[–—-]\s*.+", line):
            parts = re.split(r"\s*[–—-]\s*", line, maxsplit=1)
            current["school"] = parts[0].strip()
            current["degree"] = parts[1].strip()
    if current:
        entries.append(current)
    return entries


def _parse_skills(lines):
    skills = []
    for line in lines:
        if not line:
            continue
        for item in re.split(r"[,\|/]", line):
            item = item.strip()
            if item and len(item) > 1:
                skills.append(item)
    return skills


def _parse_projects(lines):
    entries = []
    current = {}
    for line in lines:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        if re.match(r"^[A-Z][a-zA-Z0-9\s]{2,50}$", line) and not current:
            current["name"] = line.strip()
        elif re.match(r"https?://", line):
            current["url"] = line.strip()
        else:
            current.setdefault("description", "")
            current["description"] += " " + line.strip()
    if current:
        entries.append(current)
    return entries


def _parse_simple_lines(lines):
    result = []
    for line in lines:
        item = line.strip()
        if item:
            result.append(item)
    return result


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


class ResumeParser(BaseParser):
    def parse(self, raw_data) -> dict:
        text = raw_data if isinstance(raw_data, str) else str(raw_data)
        result = self._empty_result()

        result["personal_info"]["full_name"] = _guess_name(text)

        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if emails:
            result["personal_info"]["email"] = emails[0]

        phones = re.findall(r"[\+]?[\d\-\(\)\s]{7,20}", text)
        if phones:
            result["personal_info"]["phone"] = phones[0].strip()

        sections = _split_sections(text)

        for sec_name, sec_lines in sections.items():
            if sec_name == "summary":
                result["summary"] = " ".join(ln for ln in sec_lines if ln).strip()
            elif sec_name == "experience":
                result["experience"] = _parse_experience(sec_lines)
            elif sec_name == "education":
                result["education"] = _parse_education(sec_lines)
            elif sec_name == "skills":
                result["skills"] = _parse_skills(sec_lines)
            elif sec_name == "projects":
                result["projects"] = _parse_projects(sec_lines)
            elif sec_name == "certificates":
                result["certificates"] = _parse_certificates(sec_lines)
            elif sec_name == "achievements":
                result["achievements"] = _parse_simple_lines(sec_lines)
            elif sec_name == "languages":
                result["languages"] = _parse_languages(sec_lines)
            elif sec_name == "publications":
                result["publications"] = _parse_simple_lines(sec_lines)

        return result
