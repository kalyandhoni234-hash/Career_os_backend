import re


SKILL_SYNONYMS = {
    "reactjs": "react",
    "react.js": "react",
    "react native": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "python3": "python",
    "python2": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "c++": "c++",
    "cpp": "c++",
    "c#": "c#",
    "csharp": "c#",
    ".net": ".net",
    "dotnet": ".net",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "sql": "sql",
    "mysql": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "git": "git",
    "github": "git",
    "gitlab": "git",
}


class ImportNormalizer:
    def normalize(self, raw_data: dict, source: str) -> dict:
        result = dict(raw_data)
        result["personal_info"] = self._normalize_personal_info(
            result.get("personal_info", {})
        )
        result["summary"] = (result.get("summary") or "").strip()
        result["skills"] = self.deduplicate_skills(result.get("skills", []))
        result["experience"] = self._normalize_experience(result.get("experience", []))
        result["education"] = self._normalize_education(result.get("education", []))
        result["projects"] = self._normalize_projects(result.get("projects", []))
        result["certificates"] = self._normalize_certificates(
            result.get("certificates", [])
        )
        result["languages"] = self._normalize_languages(result.get("languages", []))
        result["achievements"] = [a for a in (result.get("achievements") or []) if a]
        result["publications"] = [p for p in (result.get("publications") or []) if p]
        result["_source"] = source
        return result

    def _normalize_personal_info(self, info: dict) -> dict:
        cleaned = {}
        for key in [
            "full_name",
            "email",
            "phone",
            "location",
            "title",
            "linkedin",
            "github",
            "website",
            "portfolio",
        ]:
            val = info.get(key, "")
            cleaned[key] = val.strip() if isinstance(val, str) else ""
        return cleaned

    def _normalize_experience(self, exp_list: list) -> list:
        result = []
        seen = set()
        for exp in exp_list:
            if not isinstance(exp, dict):
                continue
            key = (exp.get("company", ""), exp.get("role", ""))
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "company": (exp.get("company") or "").strip(),
                "role": (exp.get("role") or "").strip(),
                "start": (exp.get("start") or "").strip(),
                "end": (exp.get("end") or "").strip(),
                "bullets": [b.strip() for b in (exp.get("bullets") or []) if b.strip()],
                "technologies": self.deduplicate_skills(exp.get("technologies") or []),
            }
            result.append(entry)
        return result

    def _normalize_education(self, edu_list: list) -> list:
        result = []
        seen = set()
        for edu in edu_list:
            if not isinstance(edu, dict):
                continue
            key = edu.get("school", "")
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "school": (edu.get("school") or "").strip(),
                "degree": (edu.get("degree") or "").strip(),
                "field": (edu.get("field") or "").strip(),
                "start": (edu.get("start") or "").strip(),
                "end": (edu.get("end") or "").strip(),
                "gpa": (edu.get("gpa") or "").strip(),
            }
            result.append(entry)
        return result

    def _normalize_projects(self, proj_list: list) -> list:
        result = []
        seen = set()
        for proj in proj_list:
            if not isinstance(proj, dict):
                continue
            key = proj.get("name", "")
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "name": (proj.get("name") or "").strip(),
                "description": (proj.get("description") or "").strip(),
                "technologies": self.deduplicate_skills(proj.get("technologies") or []),
                "url": (proj.get("url") or "").strip(),
            }
            result.append(entry)
        return result

    def _normalize_certificates(self, cert_list: list) -> list:
        result = []
        seen = set()
        for cert in cert_list:
            if not isinstance(cert, dict):
                continue
            key = cert.get("name", "")
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "name": (cert.get("name") or "").strip(),
                "issuer": (cert.get("issuer") or "").strip(),
                "date": (cert.get("date") or "").strip(),
            }
            result.append(entry)
        return result

    def _normalize_languages(self, lang_list: list) -> list:
        result = []
        seen = set()
        for lang in lang_list:
            if not isinstance(lang, dict):
                continue
            key = lang.get("name", "").lower().strip()
            if key in seen:
                continue
            seen.add(key)
            entry = {
                "name": (lang.get("name") or "").strip(),
                "level": (lang.get("level") or "").strip(),
            }
            result.append(entry)
        return result

    def deduplicate_skills(self, skills: list) -> list:
        seen = set()
        result = []
        for skill in skills:
            if not isinstance(skill, str):
                continue
            normalized = skill.strip().lower()
            normalized = re.sub(r"[^a-zA-Z0-9+#. _-]", "", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            mapped = SKILL_SYNONYMS.get(normalized, normalized)
            if mapped not in seen:
                seen.add(mapped)
                mapped_title = mapped[0].upper() + mapped[1:] if mapped else mapped
                result.append(mapped_title if mapped_title != mapped else mapped)
        return result

    def resolve_duplicates(self, existing_data: dict, imported_data: dict) -> dict:
        merged = dict(existing_data)
        for key in imported_data:
            if key == "personal_info":
                for field, value in imported_data["personal_info"].items():
                    if value and not merged.get("personal_info", {}).get(field):
                        merged.setdefault("personal_info", {})[field] = value
            elif key == "skills":
                existing_skills = set(
                    s.lower() for s in (existing_data.get("skills") or [])
                )
                for skill in imported_data.get("skills", []):
                    if skill.lower() not in existing_skills:
                        merged.setdefault("skills", []).append(skill)
            elif key == "experience":
                existing_keys = set(
                    (e.get("company", ""), e.get("role", ""))
                    for e in (existing_data.get("experience") or [])
                )
                for exp in imported_data.get("experience", []):
                    if (
                        exp.get("company", ""),
                        exp.get("role", ""),
                    ) not in existing_keys:
                        merged.setdefault("experience", []).append(exp)
            elif key == "education":
                existing_schools = set(
                    e.get("school", "") for e in (existing_data.get("education") or [])
                )
                for edu in imported_data.get("education", []):
                    if edu.get("school", "") not in existing_schools:
                        merged.setdefault("education", []).append(edu)
            elif key == "projects":
                existing_names = set(
                    p.get("name", "") for p in (existing_data.get("projects") or [])
                )
                for proj in imported_data.get("projects", []):
                    if proj.get("name", "") not in existing_names:
                        merged.setdefault("projects", []).append(proj)
            elif key in ("summary",):
                if not existing_data.get(key):
                    merged[key] = imported_data[key]
            elif key not in merged or not merged[key]:
                merged[key] = imported_data[key]

        return merged
