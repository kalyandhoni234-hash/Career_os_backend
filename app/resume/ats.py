import re

SKILL_VOCAB = {
    "python",
    "flask",
    "django",
    "fastapi",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "nextjs",
    "vue",
    "vue.js",
    "angular",
    "svelte",
    "node",
    "node.js",
    "nodejs",
    "deno",
    "bun",
    "java",
    "kotlin",
    "scala",
    "groovy",
    "go",
    "golang",
    "rust",
    "c++",
    "c",
    "c#",
    "csharp",
    ".net",
    "dotnet",
    "asp.net",
    "php",
    "laravel",
    "symfony",
    "ruby",
    "rails",
    "elixir",
    "phoenix",
    "swift",
    "objective-c",
    "dart",
    "flutter",
    "sql",
    "postgresql",
    "postgres",
    "mysql",
    "sqlite",
    "mariadb",
    "mongodb",
    "redis",
    "elasticsearch",
    "cassandra",
    "dynamodb",
    "firebase",
    "supabase",
    "neo4j",
    "couchdb",
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "ansible",
    "pulumi",
    "aws",
    "gcp",
    "azure",
    "cloud",
    "lambda",
    "ec2",
    "s3",
    "cloudflare",
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "ci/cd",
    "jenkins",
    "rest",
    "restful",
    "api",
    "apis",
    "graphql",
    "grpc",
    "websocket",
    "oauth",
    "jwt",
    "saml",
    "openid",
    "sso",
    "html",
    "css",
    "sass",
    "scss",
    "tailwind",
    "bootstrap",
    "material-ui",
    "redux",
    "zustand",
    "pinia",
    "vuex",
    "mobx",
    "recoil",
    "sqlalchemy",
    "prisma",
    "typeorm",
    "drizzle",
    "knex",
    "orm",
    "odm",
    "sequelize",
    "mongoose",
    "microservices",
    "soa",
    "event-driven",
    "cqrs",
    "event sourcing",
    "kafka",
    "rabbitmq",
    "nats",
    "pulsar",
    "pub/sub",
    "linux",
    "unix",
    "bash",
    "zsh",
    "powershell",
    "shell scripting",
    "testing",
    "pytest",
    "jest",
    "mocha",
    "chai",
    "cypress",
    "playwright",
    "unit testing",
    "integration testing",
    "e2e",
    "tdd",
    "bdd",
    "agile",
    "scrum",
    "kanban",
    "jira",
    "confluence",
    "notion",
    "problem-solving",
    "communication",
    "teamwork",
    "leadership",
    "data structures",
    "algorithms",
    "dsa",
    "system design",
    "machine learning",
    "ml",
    "deep learning",
    "ai",
    "llm",
    "nlp",
    "tensorflow",
    "pytorch",
    "keras",
    "scikit-learn",
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "jupyter",
    "data science",
    "docker compose",
    "helm",
    "istio",
    "linkerd",
    "envoy",
    "prometheus",
    "grafana",
    "datadog",
    "new relic",
    "sentry",
    "openapi",
    "swagger",
    "postman",
    "insomnia",
    "webpack",
    "vite",
    "esbuild",
    "rollup",
    "turbo",
    "nx",
    "storybook",
    "chromatic",
    "figma",
    "sketch",
    "adobe xd",
    "performance",
    "optimization",
    "scalability",
    "reliability",
    "security",
    "authentication",
    "authorization",
    "encryption",
    "monitoring",
    "observability",
    "logging",
    "tracing",
}

# Grouped by category for detailed ATS breakdown
SKILL_CATEGORIES = {
    "languages": {
        "python",
        "javascript",
        "typescript",
        "java",
        "kotlin",
        "scala",
        "go",
        "golang",
        "rust",
        "c++",
        "c",
        "c#",
        "csharp",
        "php",
        "ruby",
        "swift",
        "dart",
        "elixir",
        "groovy",
    },
    "frontend": {
        "react",
        "next.js",
        "nextjs",
        "vue",
        "vue.js",
        "angular",
        "svelte",
        "html",
        "css",
        "sass",
        "scss",
        "tailwind",
        "bootstrap",
        "redux",
        "zustand",
        "webpack",
        "vite",
    },
    "backend": {
        "flask",
        "django",
        "fastapi",
        "node",
        "node.js",
        "nodejs",
        "express",
        "laravel",
        "rails",
        "asp.net",
        "spring",
        "graphql",
        "grpc",
        "rest",
        "restful",
    },
    "databases": {
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "elasticsearch",
        "cassandra",
        "dynamodb",
        "firebase",
        "supabase",
    },
    "devops": {
        "docker",
        "kubernetes",
        "k8s",
        "terraform",
        "ansible",
        "aws",
        "gcp",
        "azure",
        "ci/cd",
        "jenkins",
        "linux",
        "bash",
    },
    "ai": {
        "machine learning",
        "ml",
        "deep learning",
        "ai",
        "nlp",
        "llm",
        "tensorflow",
        "pytorch",
        "pandas",
        "numpy",
        "data science",
    },
    "testing": {
        "testing",
        "pytest",
        "jest",
        "cypress",
        "playwright",
        "unit testing",
        "tdd",
    },
}

ACTION_VERBS = {
    "achieved",
    "accelerated",
    "architected",
    "automated",
    "built",
    "championed",
    "consolidated",
    "created",
    "cut",
    "decreased",
    "delivered",
    "deployed",
    "designed",
    "developed",
    "doubled",
    "drove",
    "eliminated",
    "engineered",
    "established",
    "exceeded",
    "expanded",
    "generated",
    "grew",
    "implemented",
    "improved",
    "increased",
    "initiated",
    "innovated",
    "integrated",
    "introduced",
    "launched",
    "led",
    "managed",
    "mentored",
    "migrated",
    "negotiated",
    "optimized",
    "orchestrated",
    "overhauled",
    "pioneered",
    "proposed",
    "reduced",
    "reengineered",
    "reorganized",
    "resolved",
    "restructured",
    "revamped",
    "scaled",
    "shipped",
    "simplified",
    "slashed",
    "spearheaded",
    "standardized",
    "streamlined",
    "strengthened",
    "transformed",
    "upgraded",
}

WEAK_VERBS = {
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "made",
    "got",
    "get",
    "got",
    "worked",
    "worked on",
    "helped",
    "assisted",
    "participated",
    "involved",
    "responsible for",
    "tasked with",
    "handled",
    "did",
    "done",
    "made",
    "fixed",
}


def extract_keywords(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#/\-]{1,}", text.lower())
    multi_word = set()
    lower = text.lower()
    for kw in SKILL_VOCAB:
        if " " in kw and kw in lower:
            multi_word.add(kw)
    return {w for w in words if w in SKILL_VOCAB} | multi_word


def resume_text(resume) -> str:
    parts = [resume.summary or ""]

    for exp in resume.experience or []:
        parts.append(exp.get("role", "") or "")
        parts.append(exp.get("company", "") or "")
        bullets = exp.get("bullets", "")
        if isinstance(bullets, list):
            parts.extend(bullets)
        else:
            parts.append(bullets or "")
        tech = exp.get("technologies", "")
        if isinstance(tech, list):
            parts.extend(tech)
        else:
            parts.append(tech or "")

    for edu in resume.education or []:
        parts.append(edu.get("school", "") or "")
        parts.append(edu.get("degree", "") or "")
        parts.append(edu.get("field", "") or "")

    for proj in resume.projects or []:
        parts.append(proj.get("name", "") or "")
        parts.append(proj.get("description", "") or "")
        tech = proj.get("technologies", "")
        if isinstance(tech, list):
            parts.extend(tech)
        else:
            parts.append(tech or "")

    parts.extend(resume.skills or [])
    for cert in resume.certificates or []:
        parts.append(cert.get("name", "") or "")
        parts.append(cert.get("issuer", "") or "")

    if resume.languages:
        for lang in resume.languages:
            if isinstance(lang, dict):
                parts.append(lang.get("name", "") or "")
            else:
                parts.append(str(lang))

    return " ".join(parts)


def score_resume(resume, job_description: str) -> dict:
    if not job_description:
        return {
            "overall_score": None,
            "keyword_match": 0,
            "matched": [],
            "missing": [],
            "total_keywords": 0,
            "category_scores": {},
            "action_verb_score": 0,
            "skills_density": 0,
        }

    jd_keywords = extract_keywords(job_description)
    body = resume_text(resume).lower()
    matched = sorted(kw for kw in jd_keywords if kw in body)
    missing = sorted(kw for kw in jd_keywords if kw not in body)

    keyword_match = round((len(matched) / len(jd_keywords)) * 100) if jd_keywords else 0

    # Category breakdown
    category_scores = {}
    for cat, terms in SKILL_CATEGORIES.items():
        cat_in_jd = terms & jd_keywords
        if cat_in_jd:
            cat_matched = {kw for kw in cat_in_jd if kw in body}
            category_scores[cat] = (
                round((len(cat_matched) / len(cat_in_jd)) * 100) if cat_in_jd else 100
            )

    # Action verb analysis
    exp_sentences = []
    for exp in resume.experience or []:
        bullets = exp.get("bullets", "")
        if isinstance(bullets, list):
            exp_sentences.extend(bullets)
        else:
            exp_sentences.append(bullets or "")
    exp_text = " ".join(exp_sentences).lower()
    action_verbs_found = {v for v in ACTION_VERBS if v in exp_text}
    weak_verbs_found = {
        v for v in WEAK_VERBS if re.search(rf"\b{re.escape(v)}\b", exp_text)
    }
    action_verb_score = round(
        (
            len(action_verbs_found)
            / max(len(action_verbs_found) + len(weak_verbs_found), 1)
        )
        * 100
    )

    # Skills density
    all_words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#/\-]{1,}", body)
    skill_count = len([w for w in all_words if w in SKILL_VOCAB])
    skills_density = (
        round((skill_count / max(len(all_words), 1)) * 100, 1) if all_words else 0
    )

    # Overall: weighted composite
    overall_score = round(
        keyword_match * 0.5
        + action_verb_score * 0.2
        + min(skills_density * 2, 100) * 0.15
        + len(matched) / max(len(jd_keywords), 1) * 100 * 0.15
    )

    return {
        "overall_score": overall_score,
        "keyword_match": keyword_match,
        "matched": matched,
        "missing": missing,
        "total_keywords": len(jd_keywords),
        "category_scores": category_scores,
        "action_verb_score": action_verb_score,
        "strong_verbs": sorted(action_verbs_found),
        "weak_verbs": sorted(weak_verbs_found),
        "skills_density": skills_density,
    }
