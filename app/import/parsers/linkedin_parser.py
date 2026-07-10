import re
from .base import BaseParser


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

    return sections


def _parse_name_email_from_header(lines):
    info = {}
    for line in lines:
        if not line:
            continue
        if re.search(r"@", line) and not info.get("email"):
            info["email"] = line.strip()
        elif re.search(r"linkedin\.com", line, re.IGNORECASE) and not info.get(
            "linkedin"
        ):
            info["linkedin"] = line.strip()
        elif re.search(r"\+?\d[\d\s\-\(\)]{7,}", line) and not info.get("phone"):
            info["phone"] = line.strip()
        elif (
            not info.get("full_name")
            and len(line.split()) in (2, 3)
            and not re.search(r"[@http]", line, re.IGNORECASE)
        ):
            info["full_name"] = line.strip()
    return info


def _parse_experience(lines):
    entries = []
    current = {}
    for line in lines:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        if re.match(r".+\s*[–—-]\s*.+", line) and not current:
            parts = re.split(r"\s*[–—-]\s*", line, maxsplit=1)
            current = {"role": parts[0].strip(), "company": parts[1].strip()}
        elif re.match(r"\d{4}\s*[–—-]\s*(\d{4}|Present)", line, re.IGNORECASE):
            current["end"] = line.strip()
        elif line.startswith("-") or line.startswith("•"):
            current.setdefault("bullets", []).append(line.lstrip("- •").strip())
        else:
            current.setdefault("bullets", []).append(line.strip())
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
        if not current.get("school"):
            current["school"] = line.strip()
        elif re.match(r"\d{4}\s*[–—-]\s*\d{4}", line):
            parts = re.split(r"\s*[–—-]\s*", line)
            current["start"] = parts[0].strip()
            current["end"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            current.setdefault("degree", line.strip())
    if current:
        entries.append(current)
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
    return skills


class LinkedInParser(BaseParser):
    def parse(self, raw_data) -> dict:
        text = raw_data if isinstance(raw_data, str) else str(raw_data)
        result = self._empty_result()

        sections = _split_sections(text)

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

        if not result["personal_info"].get("full_name"):
            for line in text.split("\n"):
                line = line.strip()
                if (
                    line
                    and len(line.split()) in (2, 3)
                    and not re.search(r"[@http]", line, re.IGNORECASE)
                ):
                    result["personal_info"]["full_name"] = line
                    break

        return result
