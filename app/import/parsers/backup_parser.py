from .base import BaseParser


EXPECTED_TOP_KEYS = {
    "personal_info",
    "summary",
    "experience",
    "education",
    "projects",
    "skills",
    "certificates",
    "achievements",
    "languages",
    "publications",
}

PERSONAL_INFO_FIELDS = {
    "full_name",
    "email",
    "phone",
    "location",
    "title",
    "linkedin",
    "github",
    "website",
    "portfolio",
}

EXPERIENCE_FIELDS = {"company", "role", "start", "end", "bullets", "technologies"}
EDUCATION_FIELDS = {"school", "degree", "field", "start", "end", "gpa"}
PROJECT_FIELDS = {"name", "description", "technologies", "url"}
CERTIFICATE_FIELDS = {"name", "issuer", "date"}
LANGUAGE_FIELDS = {"name", "level"}


class BackupParser(BaseParser):
    def parse(self, raw_data) -> dict:
        data = raw_data if isinstance(raw_data, dict) else {}
        result = self._empty_result()

        if not data:
            return result

        optional_keys = {
            "achievements",
            "publications",
            "certificates",
            "languages",
            "projects",
        }
        for key in EXPECTED_TOP_KEYS:
            if key not in data and key not in optional_keys:
                return result

        pi = data.get("personal_info", {})
        if not isinstance(pi, dict):
            return result
        for field in PERSONAL_INFO_FIELDS:
            if field not in pi:
                return result

        result["personal_info"] = {k: pi.get(k, "") for k in PERSONAL_INFO_FIELDS}
        result["summary"] = data.get("summary", "")

        for entry in data.get("experience", []):
            if isinstance(entry, dict) and all(f in entry for f in ("company", "role")):
                result["experience"].append(entry)

        for entry in data.get("education", []):
            if isinstance(entry, dict) and "school" in entry:
                result["education"].append(entry)

        for entry in data.get("projects", []):
            if isinstance(entry, dict) and "name" in entry:
                result["projects"].append(entry)

        for entry in data.get("certificates", []):
            if isinstance(entry, dict) and "name" in entry:
                result["certificates"].append(entry)

        for entry in data.get("languages", []):
            if isinstance(entry, dict) and "name" in entry:
                result["languages"].append(entry)

        result["skills"] = (
            data.get("skills", []) if isinstance(data.get("skills"), list) else []
        )
        result["achievements"] = (
            data.get("achievements", [])
            if isinstance(data.get("achievements"), list)
            else []
        )
        result["publications"] = (
            data.get("publications", [])
            if isinstance(data.get("publications"), list)
            else []
        )

        return result
