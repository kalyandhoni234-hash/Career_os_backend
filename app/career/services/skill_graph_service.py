from app.extensions import db
from app.career.models import SkillGraph, LearningProgress


SKILL_CATEGORIES = {
    "Backend": [
        "python",
        "flask",
        "django",
        "node",
        "express",
        "java",
        "go",
        "rust",
        "c#",
        ".net",
        "php",
        "ruby",
        "api",
        "rest",
        "graphql",
        "sqlalchemy",
    ],
    "Frontend": [
        "react",
        "vue",
        "angular",
        "svelte",
        "html",
        "css",
        "javascript",
        "typescript",
        "tailwind",
        "next.js",
        "redux",
        "webpack",
    ],
    "Databases": [
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "sqlite",
        "cassandra",
        "dynamodb",
        "elasticsearch",
        "oracle",
    ],
    "DevOps": [
        "docker",
        "kubernetes",
        "jenkins",
        "terraform",
        "ansible",
        "ci/cd",
        "github actions",
        "gitlab ci",
        "helm",
        "puppet",
    ],
    "Cloud": [
        "aws",
        "azure",
        "gcp",
        "cloud",
        "lambda",
        "ec2",
        "s3",
        "rds",
        "cloudflare",
    ],
    "AI/ML": [
        "machine learning",
        "deep learning",
        "pytorch",
        "tensorflow",
        "nlp",
        "llm",
        "rag",
        "langchain",
        "scikit-learn",
        "pandas",
        "numpy",
        "genai",
        "gemini",
        "openai",
    ],
    "Testing": [
        "pytest",
        "jest",
        "selenium",
        "cypress",
        "unittest",
        "mocha",
        "chai",
        "tdd",
        "integration testing",
    ],
    "Security": [
        "security",
        "authentication",
        "authorization",
        "jwt",
        "oauth",
        "ssl",
        "encryption",
        "penetration testing",
        "xss",
        "sql injection",
    ],
    "Networking": [
        "tcp/ip",
        "dns",
        "http",
        "load balancing",
        "cdn",
        "firewall",
        "vpn",
        "proxy",
    ],
    "Mobile": ["react native", "flutter", "swift", "kotlin", "android", "ios", "dart"],
}


def build_skill_graph(user_id):
    """Build or rebuild the skill graph from resume skills, UserSkill records, and learning progress."""
    from app.resume.models import Resume
    from app.career.models import UserSkill

    resume = Resume.query.filter_by(user_id=user_id).first()
    resume_skills = []
    if resume:
        raw_skills = resume.skills or []
        if isinstance(raw_skills, str):
            raw_skills = [raw_skills]
        for s in raw_skills:
            if isinstance(s, str):
                s = s.lower().strip()
                if s and len(s) <= 50:
                    resume_skills.append(s)

    # Also include UserSkill records (profile wizard, import, etc.)
    user_skills = UserSkill.query.filter_by(user_id=user_id).all()
    for us in user_skills:
        name = us.name.lower().strip()
        if name and len(name) <= 50 and name not in resume_skills:
            resume_skills.append(name)

    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_skills = {lp.skill_name.lower(): lp.proficiency for lp in learning}

    # Calculate proficiency per category
    category_data = {}
    for category, keywords in SKILL_CATEGORIES.items():
        matched = []
        for skill in resume_skills:
            if any(kw in skill or skill in kw for kw in keywords):
                matched.append(skill)
        for skill_name, prof in learning_skills.items():
            if any(kw in skill_name or skill_name in kw for kw in keywords):
                if skill_name not in matched:
                    matched.append(skill_name)

        if matched:
            coverage = min(100, int((len(matched) / len(keywords)) * 100))
        else:
            coverage = 0

        # Add learning progress boost
        boost = 0
        for skill_name, prof in learning_skills.items():
            if any(kw in skill_name or skill_name in kw for kw in keywords):
                boost = max(boost, prof)
        proficiency = min(100, coverage + (boost // 4))

        category_data[category] = {
            "proficiency": proficiency,
            "skill_count": len(matched),
            "skills": matched[:10],
        }

    # Persist to database
    for category, data in category_data.items():
        existing = SkillGraph.query.filter_by(
            user_id=user_id, category=category
        ).first()
        if existing:
            existing.proficiency = data["proficiency"]
            existing.skill_count = data["skill_count"]
        else:
            sg = SkillGraph(
                user_id=user_id,
                category=category,
                proficiency=data["proficiency"],
                skill_count=data["skill_count"],
            )
            db.session.add(sg)
    db.session.commit()

    return category_data


def analyze_skill_gaps(user_id, target_role=None):
    """Analyze skill gaps between current skills and a target role."""
    from app.career.models import CareerProfile, UserSkill

    # Get target info
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    target = target_role or (cp.target_role if cp else None)

    # Get current skills from Resume and UserSkill tables
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    current_skills = (
        set(s.lower().strip() for s in (resume.skills or [])) if resume else set()
    )
    user_skills = UserSkill.query.filter_by(user_id=user_id).all()
    for us in user_skills:
        name = us.name.lower().strip()
        if name:
            current_skills.add(name)

    # Get learning skills
    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_skills = {lp.skill_name.lower(): lp.proficiency for lp in learning}

    # All known skills
    all_skills = current_skills | set(learning_skills.keys())

    # Define target role skill requirements
    role_skills = _get_role_requirements(target)
    required = set(s.lower() for s in role_skills)

    if not required:
        return {
            "error": "Unknown target role",
            "target_role": target,
            "gaps": [],
            "graph": {},
        }

    # Find gaps
    missing = required - all_skills
    present = required & all_skills

    # Build gap analysis
    gaps = []
    for skill in sorted(missing):
        gaps.append(
            {
                "skill": skill,
                "priority": _get_skill_priority(skill, target),
                "estimated_ats_gain": _estimate_ats_gain(skill),
                "recommended_project": _get_recommended_project(skill),
            }
        )
    gaps.sort(key=lambda g: g["priority"], reverse=True)

    # Build skill graph analysis
    graph = build_skill_graph(user_id)
    coverage_by_category = {}
    for cat, data in graph.items():
        coverage_by_category[cat] = data["proficiency"]

    return {
        "target_role": target,
        "current_skills": sorted(current_skills),
        "learning_skills": {k: v for k, v in sorted(learning_skills.items())},
        "required_skills": sorted(required),
        "matched_skills": sorted(present),
        "missing_skills": sorted(missing),
        "coverage": int((len(present) / len(required)) * 100) if required else 0,
        "gaps": gaps,
        "graph": coverage_by_category,
    }


def _get_role_requirements(target_role):
    """Get required skills for a given target role."""
    requirements = {
        "backend engineer": [
            "python",
            "flask",
            "sql",
            "postgresql",
            "docker",
            "git",
            "rest apis",
            "testing",
            "linux",
        ],
        "backend": [
            "python",
            "flask",
            "sql",
            "postgresql",
            "docker",
            "git",
            "rest apis",
            "testing",
            "linux",
        ],
        "frontend engineer": [
            "javascript",
            "typescript",
            "react",
            "html",
            "css",
            "git",
            "rest apis",
            "testing",
        ],
        "frontend": [
            "javascript",
            "typescript",
            "react",
            "html",
            "css",
            "git",
            "rest apis",
            "testing",
        ],
        "full stack engineer": [
            "python",
            "javascript",
            "typescript",
            "react",
            "flask",
            "sql",
            "postgresql",
            "docker",
            "git",
            "rest apis",
            "testing",
        ],
        "fullstack": [
            "python",
            "javascript",
            "typescript",
            "react",
            "flask",
            "sql",
            "postgresql",
            "docker",
            "git",
            "rest apis",
            "testing",
        ],
        "ai engineer": [
            "python",
            "machine learning",
            "deep learning",
            "pytorch",
            "nlp",
            "sql",
            "docker",
            "git",
            "data analysis",
        ],
        "ai/ml engineer": [
            "python",
            "machine learning",
            "deep learning",
            "pytorch",
            "nlp",
            "sql",
            "docker",
            "git",
            "data analysis",
        ],
        "data engineer": [
            "python",
            "sql",
            "postgresql",
            "etl",
            "airflow",
            "docker",
            "git",
            "cloud",
            "spark",
        ],
        "devops engineer": [
            "linux",
            "docker",
            "kubernetes",
            "terraform",
            "ansible",
            "ci/cd",
            "git",
            "cloud",
            "monitoring",
            "python",
        ],
        "cloud engineer": [
            "cloud",
            "aws",
            "docker",
            "kubernetes",
            "terraform",
            "linux",
            "ci/cd",
            "networking",
            "python",
        ],
        "cybersecurity engineer": [
            "networking",
            "linux",
            "security",
            "python",
            "web security",
            "cryptography",
            "cloud security",
        ],
        "product manager": [
            "analytics",
            "product strategy",
            "agile",
            "user research",
            "a/b testing",
            "wireframing",
            "technical",
        ],
    }

    if target_role:
        key = target_role.lower().strip()
        if key in requirements:
            return requirements[key]
        for role_key, skills in requirements.items():
            if role_key in key or key in role_key:
                return skills

    return requirements.get("full stack engineer", [])


def _get_skill_priority(skill, target_role):
    """Get priority ranking for a missing skill (1-5)."""
    high_priority = [
        "docker",
        "sql",
        "python",
        "javascript",
        "react",
        "aws",
        "git",
        "flask",
        "typescript",
        "testing",
    ]
    medium_priority = [
        "redis",
        "mongodb",
        "kubernetes",
        "ci/cd",
        "linux",
        "rest apis",
        "terraform",
    ]
    skill_lower = skill.lower().strip()
    if skill_lower in high_priority:
        return 5
    if skill_lower in medium_priority:
        return 4
    return 3


def _estimate_ats_gain(skill):
    """Estimate ATS score gain from learning a skill."""
    gains = {
        "docker": 6,
        "sql": 5,
        "python": 8,
        "javascript": 5,
        "react": 6,
        "aws": 7,
        "git": 3,
        "flask": 4,
        "typescript": 5,
        "testing": 4,
        "redis": 4,
        "kubernetes": 7,
        "ci/cd": 5,
        "linux": 4,
        "terraform": 6,
        "mongodb": 3,
    }
    return gains.get(skill.lower().strip(), 3)


def _get_recommended_project(skill):
    """Get a recommended project for a missing skill."""
    projects = {
        "docker": "Containerize a REST API with Docker Compose",
        "sql": "Build a database-driven analytics dashboard",
        "python": "Create an automation script or CLI tool",
        "react": "Build an interactive dashboard with React",
        "aws": "Deploy a serverless application with Lambda and S3",
        "git": "Set up a monorepo with proper branching strategy",
        "flask": "Build a RESTful API with authentication",
        "redis": "Add caching and rate limiting to an existing API",
        "kubernetes": "Deploy a microservices app on Kubernetes",
        "ci/cd": "Set up GitHub Actions for automated deployment",
        "testing": "Achieve 90%+ test coverage on a project",
        "mongodb": "Build a document-based API with MongoDB",
        "typescript": "Convert a JavaScript project to TypeScript",
        "linux": "Set up a production server with bash automation",
        "terraform": "Provision cloud infrastructure with Terraform",
    }
    return projects.get(skill.lower().strip(), f"Build a project using {skill}")
