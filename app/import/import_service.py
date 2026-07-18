import logging
from datetime import datetime, timezone
from app.extensions import db
from .models import ImportRecord
from app.career.models import UserSkill
from .normalizer import ImportNormalizer
from .parsers.resume_parser import ResumeParser
from .parsers.linkedin_parser import LinkedInParser
from .parsers.github_parser import GitHubParser
from .parsers.portfolio_parser import PortfolioParser
from .parsers.backup_parser import BackupParser

logger = logging.getLogger(__name__)


PARSER_MAP = {
    "resume": ResumeParser,
    "linkedin": LinkedInParser,
    "github": GitHubParser,
    "portfolio": PortfolioParser,
    "backup": BackupParser,
}


class ImportService:
    def __init__(self, user_id):
        self.user_id = user_id
        self.normalizer = ImportNormalizer()

    def process_import(self, source: str, raw_data) -> ImportRecord:
        logger.info("Starting import for user=%s source=%s data_length=%s", self.user_id, source, len(str(raw_data)))

        record = ImportRecord(
            user_id=self.user_id,
            source=source,
            status="processing",
            raw_data=raw_data
            if isinstance(raw_data, dict)
            else {"text": str(raw_data)},
        )
        db.session.add(record)

        try:
            db.session.commit()
            logger.debug("ImportRecord created: id=%s", record.id)

            parser_cls = PARSER_MAP.get(source)
            if not parser_cls:
                raise ValueError(f"Unknown source: {source}")

            parser = parser_cls()
            logger.debug("Using parser: %s", parser_cls.__name__)

            parsed = parser.parse(raw_data)
            logger.info("Parser output: personal_info=%s, skills=%d, experience=%d, education=%d",
                       parsed.get("personal_info", {}),
                       len(parsed.get("skills", [])),
                       len(parsed.get("experience", [])),
                       len(parsed.get("education", [])))

            normalized = self.normalizer.normalize(parsed, source)
            logger.info("Normalized data: personal_info=%s, skills=%d, experience=%d, education=%d",
                       normalized.get("personal_info", {}),
                       len(normalized.get("skills", [])),
                       len(normalized.get("experience", [])),
                       len(normalized.get("education", [])))

            confidence = self._calculate_confidence(normalized)
            record.normalized_data = normalized
            record.confidence_scores = confidence
            record.import_version = "1.0"
            logger.debug("Confidence scores: %s", confidence)

            self._build_profile(record)
            self._update_resume(record)
            self._run_analyses(self.user_id)

            record.status = "completed"
            logger.info("Import completed successfully: record_id=%s", record.id)
        except Exception as e:
            db.session.rollback()
            logger.exception("Import failed for user=%s source=%s", self.user_id, source)
            record.status = "failed"
            record.error_message = f"{type(e).__name__}: {str(e)}"

        try:
            record.updated_at = datetime.now(timezone.utc)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return record

    def _confidence_label(self, val):
        if isinstance(val, list):
            return "high" if len(val) >= 3 else "medium" if val else "low"
        if isinstance(val, str):
            return (
                "high" if len(val.strip()) > 50 else "medium" if val.strip() else "low"
            )
        return "low"

    def _calculate_confidence(self, data: dict) -> dict:
        pi = data.get("personal_info", {})
        pi_filled = sum(1 for v in pi.values() if v)
        pi_total = max(len(pi), 1)
        pi_pct = round((pi_filled / pi_total) * 100)
        personal_info = "high" if pi_pct >= 80 else "medium" if pi_pct >= 40 else "low"

        skills = data.get("skills", [])
        experience = data.get("experience", [])
        education = data.get("education", [])
        projects = data.get("projects", [])

        fields_scores = {
            "personal_info": personal_info,
            "skills": self._confidence_label(skills),
            "experience": self._confidence_label(experience),
            "education": self._confidence_label(education),
            "projects": self._confidence_label(projects),
        }

        values = {"high": 3, "medium": 2, "low": 1}
        overall = round(
            sum(values.get(v, 1) for v in fields_scores.values())
            / (len(fields_scores) * 3)
            * 100
        )

        return {"overall": overall, **fields_scores}

    def _build_profile(self, record: ImportRecord):
        from app.users.models import Profile

        profile = Profile.query.filter_by(user_id=self.user_id).first()
        if not profile:
            profile = Profile(user_id=self.user_id)
            db.session.add(profile)

        nd = record.normalized_data or {}
        pi = nd.get("personal_info", {})

        if pi.get("location"):
            profile.country = pi["location"]

        skills = nd.get("skills", [])
        if skills:
            profile.skills = skills
            UserSkill.query.filter_by(user_id=self.user_id).delete()
            for name in skills:
                if isinstance(name, str) and name.strip():
                    db.session.add(UserSkill(user_id=self.user_id, name=name.strip()))

        languages = nd.get("languages", [])
        if languages:
            profile.languages = languages

    def _update_resume(self, record: ImportRecord):
        from app.resume.models import Resume

        resume = Resume.query.filter_by(user_id=self.user_id).first()
        if not resume:
            resume = Resume(user_id=self.user_id)
            db.session.add(resume)

        nd = record.normalized_data or {}
        pi = nd.get("personal_info", {})

        for field in [
            "full_name",
            "email",
            "phone",
            "location",
            "title",
            "website",
            "linkedin",
            "github",
        ]:
            val = pi.get(field)
            if val:
                setattr(resume, field, val)

        if nd.get("summary"):
            resume.summary = nd["summary"]

        if nd.get("experience"):
            resume.experience = nd["experience"]

        if nd.get("education"):
            resume.education = nd["education"]

        if nd.get("projects"):
            resume.projects = nd["projects"]

        if nd.get("skills"):
            resume.skills = nd["skills"]

        if nd.get("certificates"):
            resume.certificates = nd["certificates"]

        if nd.get("achievements"):
            resume.achievements = nd["achievements"]

        if nd.get("languages"):
            resume.languages = nd["languages"]

        if nd.get("publications"):
            resume.publications = nd["publications"]

    def _run_analyses(self, user_id):
        try:
            from app.career.services.career_score_service import compute_career_score

            compute_career_score(user_id)
        except Exception as e:
            logger.warning("Failed to compute career score: %s", e)

        try:
            from app.career.services.skill_graph_service import build_skill_graph

            build_skill_graph(user_id)
        except Exception as e:
            logger.warning("Failed to build skill graph: %s", e)

        try:
            from app.career.services.skill_graph_service import analyze_skill_gaps

            analyze_skill_gaps(user_id)
        except Exception as e:
            logger.warning("Failed to analyze skill gaps: %s", e)
