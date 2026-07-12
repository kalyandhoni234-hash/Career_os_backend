"""Project Intelligence Engine — analyzes projects and extracts metadata.

Automatically detects languages, frameworks, complexity, and computes
resume/portfolio/interview value for every project.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.extensions import db

logger = logging.getLogger(__name__)

# Framework / library detection patterns
FRAMEWORK_PATTERNS: dict[str, list[str]] = {
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs", "angular.js"],
    "vue": ["vue", "vuejs", "vue.js"],
    "next.js": ["next", "nextjs", "next.js"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "express": ["express"],
    "spring": ["spring", "spring boot"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "tailwind": ["tailwind", "tailwindcss"],
    "redux": ["redux"],
    "graphql": ["graphql", "gql"],
    "langchain": ["langchain"],
}

SKILL_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "django", "flask", "fastapi", "pytorch", "tensorflow", "pandas", "numpy"],
    "javascript": ["javascript", "js", "react", "vue", "angular", "node", "express", "next"],
    "typescript": ["typescript", "ts", "angular", "next"],
    "java": ["java", "spring", "maven", "gradle"],
    "docker": ["docker", "dockerfile", "container"],
    "kubernetes": ["kubernetes", "k8s", "helm"],
    "sql": ["sql", "postgresql", "mysql", "database", "sqlite"],
    "machine learning": ["machine learning", "ml", "tensorflow", "pytorch", "sklearn", "scikit-learn"],
    "react": ["react", "reactjs", "jsx", "redux"],
    "node.js": ["node", "nodejs", "express", "npm"],
    "aws": ["aws", "s3", "lambda", "ec2", "cloudformation"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "github actions", "jenkins", "gitlab ci"],
}


def analyze_project(project_id: int) -> dict[str, Any] | None:
    """Analyze a project and create/update its intelligence metadata."""
    from app.intelligence.models import CanonicalProject, ProjectIntelligence

    project = CanonicalProject.query.get(project_id)
    if not project:
        return None

    languages = _detect_languages(project)
    frameworks = _detect_frameworks(project, languages)
    libraries = _detect_libraries(project)
    complexity = _estimate_complexity(project, languages, frameworks)
    domain = _detect_domain(project)
    inferred_skills = _infer_skills(project, languages, frameworks)
    estimated_skill_level = _estimate_skill_level(complexity, inferred_skills)

    resume_value = _compute_resume_value(project, complexity, languages, frameworks)
    portfolio_value = _compute_portfolio_value(project, complexity, languages)
    interview_value = _compute_interview_value(project, complexity, frameworks, domain)
    learning_value = _compute_learning_value(project, complexity, inferred_skills)

    pi = ProjectIntelligence.query.filter_by(project_id=project_id).first()
    now = datetime.now(timezone.utc)

    if not pi:
        pi = ProjectIntelligence(
            user_id=project.user_id,
            project_id=project_id,
        )
        db.session.add(pi)

    pi.languages_detected = languages
    pi.frameworks_detected = frameworks
    pi.libraries_detected = libraries
    pi.complexity = complexity
    pi.domain = domain
    pi.estimated_skill_level = estimated_skill_level
    pi.inferred_skills = inferred_skills
    pi.resume_value = resume_value
    pi.portfolio_value = portfolio_value
    pi.interview_value = interview_value
    pi.learning_value = learning_value
    pi.last_analyzed_at = now

    # Check for README
    pi.has_readme = bool(project.readme_url or project.description)

    db.session.commit()

    return _serialize(pi)


def _detect_languages(project: Any) -> list[str]:
    """Detect languages from project data."""
    languages = set()

    if project.primary_language:
        languages.add(project.primary_language)

    if project.languages:
        for lang in project.languages:
            if isinstance(lang, str):
                languages.add(lang)

    if project.topics:
        for topic in project.topics:
            t = topic.lower()
            for lang_name, keywords in SKILL_KEYWORDS.items():
                if any(kw in t for kw in keywords):
                    languages.add(lang_name)

    if project.description:
        desc = project.description.lower()
        for lang_name, keywords in SKILL_KEYWORDS.items():
            if any(kw in desc for kw in keywords):
                languages.add(lang_name)

    return sorted(languages)


def _detect_frameworks(project: Any, languages: list[str]) -> list[str]:
    """Detect frameworks from project data."""
    frameworks = set()

    text = f"{project.description or ''} {' '.join(project.topics or [])} {' '.join(languages)}".lower()
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        if any(p in text for p in patterns):
            frameworks.add(framework)

    return sorted(frameworks)


def _detect_libraries(project: Any) -> list[str]:
    """Detect notable libraries from project topics/description."""
    notable = []
    lib_keywords = ["pandas", "numpy", "requests", "axios", "lodash", "jquery",
                    "bootstrap", "material-ui", "chakra", "shadcn", "three.js",
                    "chart.js", "d3.js", "socket.io"]
    text = f"{' '.join(project.topics or [])} {project.description or ''}".lower()
    for lib in lib_keywords:
        if lib in text:
            notable.append(lib)
    return notable


def _estimate_complexity(project: Any, languages: list[str], frameworks: list[str]) -> str:
    """Estimate project complexity based on available signals."""
    score = 0

    if len(languages) > 2:
        score += 2
    elif len(languages) > 1:
        score += 1

    if len(frameworks) > 1:
        score += 2
    elif len(frameworks) > 0:
        score += 1

    advanced_frameworks = {"kubernetes", "tensorflow", "pytorch", "spring", "langchain", "graphql"}
    if any(f in advanced_frameworks for f in frameworks):
        score += 2

    if project.stars and project.stars > 50:
        score += 1
    if not project.is_fork:
        score += 1
    if project.description and len(project.description) > 200:
        score += 1

    if score <= 2:
        return "beginner"
    elif score <= 4:
        return "intermediate"
    return "advanced"


def _detect_domain(project: Any) -> str:
    """Detect the project domain from its metadata."""
    text = f"{project.name or ''} {project.description or ''} {' '.join(project.topics or [])}".lower()

    domain_patterns = {
        "web": ["web", "website", "api", "rest", "fullstack", "frontend", "backend", "saas"],
        "mobile": ["mobile", "android", "ios", "flutter", "react native"],
        "data_science": ["data", "analytics", "ml", "machine learning", "deep learning", "ai"],
        "devops": ["devops", "infrastructure", "deployment", "docker", "kubernetes", "ci/cd"],
        "security": ["security", "cybersecurity", "encryption", "auth", "penetration"],
        "blockchain": ["blockchain", "web3", "solidity", "crypto", "nft"],
        "game": ["game", "gaming", "unity", "unreal"],
        "cli": ["cli", "terminal", "command line", "tool"],
    }

    for domain, keywords in domain_patterns.items():
        if any(kw in text for kw in keywords):
            return domain

    return "general"


def _infer_skills(project: Any, languages: list[str], frameworks: list[str]) -> list[str]:
    """Infer skills from project data."""
    skills = set(languages + frameworks)
    text = f"{project.description or ''} {' '.join(project.topics or [])}".lower()

    for skill, keywords in SKILL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            skills.add(skill)

    return sorted(skills)


def _estimate_skill_level(complexity: str, inferred_skills: list[str]) -> str:
    """Estimate the user's skill level based on project analysis."""
    if complexity == "advanced" and len(inferred_skills) > 3:
        return "advanced"
    elif complexity == "intermediate" or len(inferred_skills) > 5:
        return "intermediate"
    return "beginner"


def _compute_resume_value(project: Any, complexity: str, languages: list[str], frameworks: list[str]) -> int:
    """How valuable this project is for a resume."""
    score = 20  # baseline for having a project
    complexity_values = {"beginner": 0, "intermediate": 15, "advanced": 30}
    score += complexity_values.get(complexity, 0)
    score += min(20, len(languages) * 5)
    score += min(15, len(frameworks) * 5)
    if project.stars and project.stars > 10:
        score += 10
    if not project.is_fork:
        score += 10
    if project.description and len(project.description) > 100:
        score += 5
    return min(100, score)


def _compute_portfolio_value(project: Any, complexity: str, languages: list[str]) -> int:
    """How valuable this project is for a portfolio."""
    score = 15
    complexity_values = {"beginner": 0, "intermediate": 10, "advanced": 25}
    score += complexity_values.get(complexity, 0)
    if project.url:
        score += 15
    if project.is_pinned:
        score += 15
    if not project.is_fork:
        score += 10
    if project.readme_url:
        score += 10
    if project.stars and project.stars > 5:
        score += 10
    return min(100, score)


def _compute_interview_value(project: Any, complexity: str, frameworks: list[str], domain: str) -> int:
    """How valuable this project is in an interview context."""
    score = 10
    complexity_values = {"beginner": 0, "intermediate": 10, "advanced": 25}
    score += complexity_values.get(complexity, 0)
    in_demand_frameworks = {"react", "angular", "spring", "pytorch", "tensorflow", "kubernetes", "docker"}
    score += min(25, sum(5 for f in frameworks if f in in_demand_frameworks))
    if domain and domain != "general":
        score += 10
    if project.description and len(project.description) > 100:
        score += 5
    if project.stars and project.stars > 20:
        score += 10
    return min(100, score)


def _compute_learning_value(project: Any, complexity: str, inferred_skills: list[str]) -> int:
    """How much learning value this project provides."""
    score = 10
    complexity_values = {"beginner": 5, "intermediate": 10, "advanced": 15}
    score += complexity_values.get(complexity, 0)
    score += min(25, len(inferred_skills) * 3)
    if not project.is_fork:
        score += 15
    if project.description:
        score += 5
    return min(100, score)


def _serialize(pi: Any) -> dict:
    """Serialize a ProjectIntelligence record to a dict."""
    return {
        "id": pi.id,
        "project_id": pi.project_id,
        "languages_detected": pi.languages_detected,
        "frameworks_detected": pi.frameworks_detected,
        "libraries_detected": pi.libraries_detected,
        "complexity": pi.complexity,
        "domain": pi.domain,
        "estimated_skill_level": pi.estimated_skill_level,
        "has_readme": pi.has_readme,
        "has_tests": pi.has_tests,
        "has_documentation": pi.has_documentation,
        "has_ci": pi.has_ci,
        "has_dockerfile": pi.has_dockerfile,
        "inferred_skills": pi.inferred_skills,
        "resume_value": pi.resume_value,
        "portfolio_value": pi.portfolio_value,
        "interview_value": pi.interview_value,
        "learning_value": pi.learning_value,
        "last_analyzed_at": pi.last_analyzed_at.isoformat() if pi.last_analyzed_at else None,
    }


def get_project_intelligence(project_id: int) -> dict | None:
    """Get project intelligence for a specific project."""
    from app.intelligence.models import ProjectIntelligence
    pi = ProjectIntelligence.query.filter_by(project_id=project_id).first()
    if not pi:
        return None
    return _serialize(pi)


def get_all_project_intelligence(user_id: int) -> list[dict]:
    """Get project intelligence for all user projects."""
    from app.intelligence.models import ProjectIntelligence, CanonicalProject

    results = []
    projects = CanonicalProject.query.filter_by(user_id=user_id).all()
    for p in projects:
        pi = ProjectIntelligence.query.filter_by(project_id=p.id).first()
        if pi:
            results.append({**_serialize(pi), "project_name": p.name})
    return results
