import logging

from app.extensions import db
from app.career.models import SkillGraph, LearningProgress
from app.career.services.skill_maps import get_role_skill_map

logger = logging.getLogger(__name__)

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

    user_skills = UserSkill.query.filter_by(user_id=user_id).all()
    for us in user_skills:
        name = us.name.lower().strip()
        if name and len(name) <= 50 and name not in resume_skills:
            resume_skills.append(name)

    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_skills = {lp.skill_name.lower(): lp.proficiency for lp in learning}

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
    """Analyze skill gaps using curated role-specific skill maps with explainability."""
    from app.career.models import CareerProfile, UserSkill

    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    target = target_role or (cp.target_role if cp else None)

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

    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_skills = {lp.skill_name.lower(): lp.proficiency for lp in learning}

    all_skills = current_skills | set(learning_skills.keys())

    # Look up curated skill map
    rsm = get_role_skill_map(target)

    if not rsm:
        logger.warning("No curated skill map found for role '%s'", target)
        graph = build_skill_graph(user_id)
        return {
            "error": "Unknown target role",
            "target_role": target,
            "gaps": [],
            "graph": {cat: data["proficiency"] for cat, data in graph.items()},
        }

    # Analyze each skill in the map
    required_skills = []
    matched_skills = []
    missing_skills = []
    gaps = []
    coverage_by_tier = {"core": {"total": 0, "matched": 0},
                        "intermediate": {"total": 0, "matched": 0},
                        "advanced": {"total": 0, "matched": 0}}

    # Sort skills by tier order for consistent output
    tier_order = {"core": 0, "intermediate": 1, "advanced": 2}

    sorted_skills = sorted(
        rsm.skills.values(),
        key=lambda s: (tier_order.get(s.tier, 99), -s.priority, s.name),
    )

    for skill_info in sorted_skills:
        skill_name = skill_info.name.lower().strip()
        required_skills.append(skill_name)

        coverage_by_tier[skill_info.tier]["total"] += 1

        # Check if user has this skill (exact match or substring containment)
        has_skill = False
        user_has_this = set()

        for us in all_skills:
            us_lower = us.lower().strip()
            if skill_name in us_lower or us_lower in skill_name:
                has_skill = True
                user_has_this.add(us)
                break

        if has_skill:
            matched_skills.append(skill_name)
            coverage_by_tier[skill_info.tier]["matched"] += 1
        else:
            missing_skills.append(skill_name)
            gaps.append({
                "skill": skill_name,
                "priority": skill_info.priority,
                "tier": skill_info.tier,
                "reason": skill_info.reason,
                "learning_time_weeks": skill_info.learning_time_weeks,
                "resources": skill_info.resources,
                "unlocks": skill_info.unlocks,
                "estimated_ats_gain": skill_info.ats_gain,
                "recommended_project": _project_for_skill(skill_name, rsm.title),
            })

    # Calculate coverage
    total_required = len(required_skills)
    total_matched = len(matched_skills)
    coverage = int((total_matched / total_required) * 100) if total_required else 0

    # Per-tier coverage percentages
    tier_coverage = {}
    for tier, counts in coverage_by_tier.items():
        if counts["total"] > 0:
            tier_coverage[tier] = int((counts["matched"] / counts["total"]) * 100)
        else:
            tier_coverage[tier] = 100

    graph = build_skill_graph(user_id)
    coverage_by_category = {cat: data["proficiency"] for cat, data in graph.items()}

    # Build learning roadmap
    roadmap = _build_learning_roadmap(gaps, rsm)

    return {
        "target_role": rsm.title,
        "role_description": rsm.description,
        "estimated_months": rsm.estimated_months,
        "current_skills": sorted(current_skills),
        "learning_skills": {k: v for k, v in sorted(learning_skills.items())},
        "required_skills": sorted(required_skills),
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),
        "coverage": coverage,
        "coverage_by_tier": tier_coverage,
        "gaps": gaps,
        "graph": coverage_by_category,
        "roadmap": roadmap,
    }


def _build_learning_roadmap(gaps, rsm):
    """Build a phased learning roadmap from identified skill gaps."""
    core_gaps = [g for g in gaps if g["tier"] == "core"]
    intermediate_gaps = [g for g in gaps if g["tier"] == "intermediate"]
    advanced_gaps = [g for g in gaps if g["tier"] == "advanced"]

    core_gaps.sort(key=lambda g: (-g["priority"], g["learning_time_weeks"]))
    intermediate_gaps.sort(key=lambda g: (-g["priority"], g["learning_time_weeks"]))
    advanced_gaps.sort(key=lambda g: (-g["priority"], g["learning_time_weeks"]))

    phases = []

    if core_gaps:
        total_weeks = sum(g["learning_time_weeks"] for g in core_gaps)
        phases.append({
            "phase": 1,
            "title": "Core Foundations",
            "description": "Master the fundamental skills required for this role",
            "months_estimated": max(1, round(total_weeks / 4)),
            "skills": core_gaps,
        })

    if intermediate_gaps:
        total_weeks = sum(g["learning_time_weeks"] for g in intermediate_gaps)
        phases.append({
            "phase": 2,
            "title": "Intermediate Skills",
            "description": "Build on your foundation with specialized competencies",
            "months_estimated": max(1, round(total_weeks / 4)),
            "skills": intermediate_gaps,
        })

    if advanced_gaps:
        total_weeks = sum(g["learning_time_weeks"] for g in advanced_gaps)
        phases.append({
            "phase": 3,
            "title": "Advanced Specialization",
            "description": "Develop expert-level proficiency in niche areas",
            "months_estimated": max(1, round(total_weeks / 4)),
            "skills": advanced_gaps,
        })

    return {"phases": phases, "total_months_estimated": rsm.estimated_months}


_PROJECT_TEMPLATES = {
    "ethical hacker": {
        "networking": "Set up a segmented home lab with pfSense, VLANs, and monitor traffic between segments",
        "linux": "Harden a Linux server by configuring SELinux, auditd, and fail2ban",
        "web application security": "Execute a full OWASP Top 10 assessment on a deliberately vulnerable web app (DVWA/WebGoat)",
        "penetration testing methodology": "Conduct a full-scope penetration test on HackTheBox or Proving Grounds, documenting each phase",
        "vulnerability assessment": "Run a Nessus vulnerability scan on a home lab environment and prioritize findings by CVSS score",
        "bash scripting": "Write a bash script that automates reconnaissance: subdomain enumeration, port scanning, and service discovery",
        "python": "Build a custom vulnerability scanner that checks for common misconfigurations across a network range",
        "nmap": "Perform a comprehensive network discovery scan with service fingerprinting and OS detection on a lab network",
        "burp suite": "Complete all PortSwigger Web Security Academy labs using Burp Suite Pro",
        "wireshark": "Capture and analyze 10 common network attacks (ARP spoofing, DNS poisoning, SYN flood) in Wireshark",
        "metasploit": "Set up Metasploit to automate exploitation of a Windows 10 VM, including privilege escalation and persistence",
        "sql injection": "Write a blind SQL injection script that extracts data from a MySQL database character by character",
        "cryptography": "Implement a TLS 1.3 handshake analysis tool that validates certificate chains and cipher suite strength",
        "reverse engineering": "Reverse-engineer a simple CrackMe binary to find the correct password using Ghidra",
        "malware analysis": "Perform static and dynamic analysis of a real malware sample in a sandboxed environment",
        "cloud security": "Audit an AWS account for 20 common security misconfigurations using ScoutSuite or Prowler",
        "exploit development": "Develop a buffer overflow exploit for a custom vulnerable service with ASLR bypass",
        "digital forensics": "Conduct a full forensic investigation of a compromised VM: acquire memory, analyze artifacts, write report",
        "social engineering": "Design and execute an ethical phishing campaign using Gophish with employee awareness training materials",
    },
    "full stack developer": {
        "html": "Build a semantic HTML5 page with proper accessibility landmarks and ARIA attributes",
        "css": "Recreate a complex landing page layout using CSS Grid, Flexbox, and custom properties",
        "javascript": "Build a real-time collaborative todo app with vanilla JavaScript and localStorage sync",
        "react": "Create a full-stack dashboard with React, React Router, and state management",
        "rest apis": "Design and document a RESTful API with OpenAPI/Swagger specification",
        "sql": "Design and implement a normalized database schema for an e-commerce platform",
        "git": "Set up a monorepo with Git submodules, hooks, and a standardized branching strategy",
        "node.js": "Build a real-time chat server with Node.js, WebSockets, and JWT authentication",
        "postgresql": "Optimize a PostgreSQL database with indexes, materialized views, and query tuning",
        "typescript": "Migrate a JavaScript React project to TypeScript with strict mode and generic components",
        "testing": "Achieve 90%+ test coverage on a React app using Jest, React Testing Library, and Cypress",
        "next.js": "Build a marketing site with Next.js App Router, SSR, ISR, and dynamic metadata",
        "tailwind css": "Build a fully responsive UI component library using Tailwind CSS and headless UI",
        "docker": "Containerize a full-stack app with Docker Compose (React + Node + PostgreSQL + Redis)",
        "ci/cd": "Set up GitHub Actions pipelines for lint, test, build, and deploy to staging/production",
        "graphql": "Build a GraphQL API gateway that aggregates data from three REST microservices",
        "redis": "Implement caching, rate limiting, and session management with Redis in a Node.js API",
        "cloud": "Deploy a serverless full-stack app using AWS Lambda, API Gateway, DynamoDB, and S3",
        "system design": "Design and document a scalable URL shortener with load estimation and capacity planning",
        "prisma": "Build a type-safe API with Prisma ORM, migrations, and relational queries",
    },
    "ai engineer": {
        "python": "Build a data processing pipeline that ingests, cleans, and featurizes 10 GB of raw data",
        "machine learning": "Train and compare 5 classification models on a real dataset, documenting performance trade-offs",
        "pytorch": "Implement a custom CNN from scratch in PyTorch and train it on CIFAR-10",
        "pandas": "Write a pandas pipeline that cleans, transforms, and performs feature engineering on a messy dataset",
        "numpy": "Implement matrix operations (dot product, SVD, eigen decomposition) using only NumPy",
        "sql": "Build a feature extraction pipeline that queries a PostgreSQL database and generates training data",
        "git": "Set up DVC (Data Version Control) with Git for versioning datasets and model checkpoints",
        "mathematics": "Implement gradient descent, PCA, and linear regression from scratch in Python",
        "natural language processing": "Build a text classification system that processes and classifies 100K documents",
        "deep learning": "Train a transformer model from scratch on a custom dataset and evaluate its performance",
        "scikit-learn": "Build an automated ML pipeline with scikit-learn pipelines, grid search, and cross-validation",
        "mlops": "Deploy an ML model as a REST API with Docker, model versioning, and A/B testing infrastructure",
        "docker": "Containerize a training pipeline with GPU support and reproducible dependencies",
        "llm": "Build a RAG (Retrieval-Augmented Generation) system using LangChain, ChromaDB, and an open-source LLM",
        "computer vision": "Train an object detection model using YOLO or Detectron2 on a custom dataset",
        "cloud ml services": "Deploy and monitor a model on SageMaker with auto-scaling and drift detection",
        "experiment tracking": "Set up MLflow to track 50+ experiments with hyperparameters, metrics, and model registry",
        "data engineering": "Build an ETL pipeline that ingests streaming data, transforms it, and stores it in a feature store",
    },
}


def _project_for_skill(skill_name, role_title):
    """Generate a recommended project for a missing skill, role-aware when possible."""
    role_key = role_title.lower().strip()
    templates = _PROJECT_TEMPLATES.get(role_key, {})

    if skill_name in templates:
        return templates[skill_name]

    # Fallback: generic project
    fallback = {
        "python": "Create an automation script or CLI tool using Python",
        "docker": "Containerize an application with Docker Compose",
        "sql": "Build a database-driven analytics dashboard",
        "react": "Build an interactive dashboard with React",
        "javascript": "Create a dynamic single-page application",
        "git": "Set up a monorepo with proper branching strategy",
        "linux": "Set up a production server with bash automation",
        "aws": "Deploy a serverless application with Lambda and S3",
        "testing": "Achieve 90%+ test coverage on an existing project",
    }
    return fallback.get(skill_name, f"Build a practical project using {skill_name}")
