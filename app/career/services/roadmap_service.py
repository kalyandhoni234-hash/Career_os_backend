from datetime import datetime, timezone
from app.extensions import db
from app.career.models import Roadmap, RoadmapNode, LearningProgress


ROADMAP_TEMPLATES = {
    "backend": {
        "title": "Backend Engineer",
        "description": "Master backend development with APIs, databases, and cloud services.",
        "nodes": [
            {"week": 1, "title": "Python Fundamentals", "description": "Review advanced Python concepts: decorators, generators, context managers", "skill_tags": ["Python"], "resource_type": "course"},
            {"week": 2, "title": "RESTful APIs with Flask", "description": "Build REST APIs with Flask, request validation, error handling", "skill_tags": ["Flask", "REST APIs"], "resource_type": "course"},
            {"week": 3, "title": "Database Design & SQL", "description": "Learn relational DB design, complex queries, indexing, and ORMs", "skill_tags": ["SQL", "PostgreSQL"], "resource_type": "course"},
            {"week": 4, "title": "Docker & Containerization", "description": "Containerize applications with Docker, Docker Compose, multi-stage builds", "skill_tags": ["Docker"], "resource_type": "course"},
            {"week": 5, "title": "Redis & Caching", "description": "Implement caching strategies with Redis, rate limiting, session storage", "skill_tags": ["Redis"], "resource_type": "course"},
            {"week": 6, "title": "Message Queues", "description": "Learn async processing with Celery and RabbitMQ/Redis", "skill_tags": ["Celery", "Redis"], "resource_type": "course"},
            {"week": 7, "title": "AWS Fundamentals", "description": "Deploy applications on AWS EC2, S3, RDS, Lambda", "skill_tags": ["AWS"], "resource_type": "course"},
            {"week": 8, "title": "CI/CD Pipeline", "description": "Set up GitHub Actions for automated testing and deployment", "skill_tags": ["CI/CD", "GitHub Actions"], "resource_type": "course"},
            {"week": 9, "title": "Testing & TDD", "description": "Write unit tests, integration tests, and end-to-end tests", "skill_tags": ["Testing", "Python"], "resource_type": "course"},
            {"week": 10, "title": "API Security", "description": "Implement authentication, authorization, rate limiting, input validation", "skill_tags": ["Security", "JWT"], "resource_type": "course"},
            {"week": 11, "title": "Build Portfolio Project", "description": "Create a production-ready REST API with all learned technologies", "skill_tags": ["Flask", "Docker", "AWS", "PostgreSQL"], "resource_type": "project"},
            {"week": 12, "title": "System Design Basics", "description": "Learn scalability, load balancing, microservices patterns", "skill_tags": ["System Design"], "resource_type": "course"},
        ],
    },
    "frontend": {
        "title": "Frontend Engineer",
        "description": "Master modern frontend development with React, TypeScript, and responsive design.",
        "nodes": [
            {"week": 1, "title": "JavaScript Deep Dive", "description": "ES6+, async/await, closures, prototypes, modules", "skill_tags": ["JavaScript"], "resource_type": "course"},
            {"week": 2, "title": "TypeScript Fundamentals", "description": "Types, interfaces, generics, advanced types", "skill_tags": ["TypeScript"], "resource_type": "course"},
            {"week": 3, "title": "React Essentials", "description": "Components, hooks, state management, context", "skill_tags": ["React"], "resource_type": "course"},
            {"week": 4, "title": "Next.js & SSR", "description": "App Router, server components, data fetching, routing", "skill_tags": ["Next.js", "React"], "resource_type": "course"},
            {"week": 5, "title": "CSS & Tailwind", "description": "Modern CSS, flexbox, grid, Tailwind CSS, responsive design", "skill_tags": ["CSS", "Tailwind"], "resource_type": "course"},
            {"week": 6, "title": "State Management", "description": "Zustand, Jotai, or Redux Toolkit for complex state", "skill_tags": ["React", "State Management"], "resource_type": "course"},
            {"week": 7, "title": "Testing Frontend", "description": "Jest, React Testing Library, Cypress for E2E", "skill_tags": ["Testing", "JavaScript"], "resource_type": "course"},
            {"week": 8, "title": "Performance Optimization", "description": "Lighthouse, lazy loading, code splitting, bundle analysis", "skill_tags": ["Performance"], "resource_type": "course"},
            {"week": 9, "title": "Accessibility (a11y)", "description": "ARIA, keyboard navigation, screen readers, WCAG standards", "skill_tags": ["Accessibility"], "resource_type": "course"},
            {"week": 10, "title": "Build Portfolio Project", "description": "Create a full-featured Next.js application", "skill_tags": ["Next.js", "React", "TypeScript"], "resource_type": "project"},
            {"week": 11, "title": "API Integration", "description": "REST clients, GraphQL, WebSockets, real-time data", "skill_tags": ["REST APIs", "GraphQL"], "resource_type": "course"},
            {"week": 12, "title": "Deployment & CI/CD", "description": "Vercel, Netlify, GitHub Actions, environment management", "skill_tags": ["CI/CD", "DevOps"], "resource_type": "course"},
        ],
    },
    "fullstack": {
        "title": "Full Stack Engineer",
        "description": "Become proficient in both frontend and backend development.",
        "nodes": [
            {"week": 1, "title": "Python & JavaScript Review", "description": "Core concepts in both languages", "skill_tags": ["Python", "JavaScript"], "resource_type": "course"},
            {"week": 2, "title": "REST APIs with Flask", "description": "Build APIs with Flask and SQLAlchemy", "skill_tags": ["Flask", "Python"], "resource_type": "course"},
            {"week": 3, "title": "React Frontend", "description": "Build UIs with React components and hooks", "skill_tags": ["React", "JavaScript"], "resource_type": "course"},
            {"week": 4, "title": "Database Design", "description": "SQL, migrations, relationships, query optimization", "skill_tags": ["SQL", "PostgreSQL"], "resource_type": "course"},
            {"week": 5, "title": "Full Stack Integration", "description": "Connect frontend to backend, authentication flow, CORS", "skill_tags": ["React", "Flask"], "resource_type": "project"},
            {"week": 6, "title": "Docker & Deployment", "description": "Containerize full stack app, deploy to cloud", "skill_tags": ["Docker", "AWS"], "resource_type": "course"},
            {"week": 7, "title": "Testing Full Stack", "description": "Unit, integration, and E2E testing for entire stack", "skill_tags": ["Testing", "Python", "JavaScript"], "resource_type": "course"},
            {"week": 8, "title": "DevOps Basics", "description": "CI/CD, monitoring, logging, environment management", "skill_tags": ["CI/CD", "DevOps"], "resource_type": "course"},
        ],
    },
    "ai": {
        "title": "AI Engineer",
        "description": "Build AI-powered applications with machine learning and LLMs.",
        "nodes": [
            {"week": 1, "title": "Python for AI/ML", "description": "NumPy, Pandas, data manipulation", "skill_tags": ["Python"], "resource_type": "course"},
            {"week": 2, "title": "Machine Learning Fundamentals", "description": "Supervised/unsupervised learning, scikit-learn", "skill_tags": ["Machine Learning"], "resource_type": "course"},
            {"week": 3, "title": "Deep Learning with PyTorch", "description": "Neural networks, CNNs, RNNs, transfer learning", "skill_tags": ["PyTorch", "Deep Learning"], "resource_type": "course"},
            {"week": 4, "title": "NLP & Transformers", "description": "Tokenization, embeddings, BERT, GPT, Hugging Face", "skill_tags": ["NLP", "Transformers"], "resource_type": "course"},
            {"week": 5, "title": "LLM Application Development", "description": "RAG, prompt engineering, LangChain, vector databases", "skill_tags": ["LLMs", "RAG"], "resource_type": "course"},
            {"week": 6, "title": "MLOps & Deployment", "description": "Model serving, Docker, MLflow, monitoring", "skill_tags": ["MLOps", "Docker"], "resource_type": "course"},
            {"week": 7, "title": "Data Engineering Basics", "description": "ETL pipelines, feature stores, data validation", "skill_tags": ["Data Engineering"], "resource_type": "course"},
            {"week": 8, "title": "Build AI Project", "description": "End-to-end AI application with a trained model", "skill_tags": ["Python", "PyTorch", "Docker"], "resource_type": "project"},
        ],
    },
    "cybersecurity": {
        "title": "Cybersecurity Engineer",
        "description": "Protect systems and networks from digital threats.",
        "nodes": [
            {"week": 1, "title": "Networking Fundamentals", "description": "TCP/IP, DNS, HTTP, network protocols", "skill_tags": ["Networking"], "resource_type": "course"},
            {"week": 2, "title": "Operating System Security", "description": "Linux security, permissions, hardening", "skill_tags": ["Linux", "Security"], "resource_type": "course"},
            {"week": 3, "title": "Web Application Security", "description": "OWASP Top 10, XSS, SQL injection, CSRF", "skill_tags": ["Web Security"], "resource_type": "course"},
            {"week": 4, "title": "Cryptography", "description": "Encryption, hashing, digital signatures, TLS", "skill_tags": ["Cryptography"], "resource_type": "course"},
            {"week": 5, "title": "Penetration Testing", "description": "Metasploit, Burp Suite, vulnerability scanning", "skill_tags": ["Penetration Testing"], "resource_type": "course"},
            {"week": 6, "title": "Security Operations", "description": "SIEM, incident response, threat intelligence", "skill_tags": ["Security Operations"], "resource_type": "course"},
            {"week": 7, "title": "Cloud Security", "description": "AWS security, IAM, security groups, compliance", "skill_tags": ["Cloud Security", "AWS"], "resource_type": "course"},
            {"week": 8, "title": "Capture The Flag", "description": "Practice with CTF challenges and build a security portfolio", "skill_tags": ["Security"], "resource_type": "project"},
        ],
    },
    "cloud": {
        "title": "Cloud Engineer",
        "description": "Design and manage cloud infrastructure on AWS/Azure/GCP.",
        "nodes": [
            {"week": 1, "title": "Cloud Fundamentals", "description": "IaaS, PaaS, SaaS, cloud deployment models", "skill_tags": ["Cloud Computing"], "resource_type": "course"},
            {"week": 2, "title": "AWS Core Services", "description": "EC2, S3, VPC, IAM, RDS", "skill_tags": ["AWS"], "resource_type": "course"},
            {"week": 3, "title": "Infrastructure as Code", "description": "Terraform, CloudFormation, declarative infrastructure", "skill_tags": ["Terraform", "IaC"], "resource_type": "course"},
            {"week": 4, "title": "Container Orchestration", "description": "Kubernetes, pods, services, deployments, Helm", "skill_tags": ["Kubernetes", "Docker"], "resource_type": "course"},
            {"week": 5, "title": "CI/CD on Cloud", "description": "GitHub Actions, CodePipeline, automated deployments", "skill_tags": ["CI/CD", "AWS"], "resource_type": "course"},
            {"week": 6, "title": "Monitoring & Observability", "description": "CloudWatch, Prometheus, Grafana, logging", "skill_tags": ["Monitoring", "DevOps"], "resource_type": "course"},
            {"week": 7, "title": "Cloud Security", "description": "Security groups, encryption, compliance, auditing", "skill_tags": ["Cloud Security"], "resource_type": "course"},
            {"week": 8, "title": "Build Cloud Infrastructure", "description": "Design and deploy a scalable cloud architecture", "skill_tags": ["AWS", "Terraform", "Docker"], "resource_type": "project"},
        ],
    },
    "devops": {
        "title": "DevOps Engineer",
        "description": "Automate infrastructure, deployments, and operations.",
        "nodes": [
            {"week": 1, "title": "Linux Administration", "description": "Shell scripting, process management, system administration", "skill_tags": ["Linux"], "resource_type": "course"},
            {"week": 2, "title": "Git & Version Control", "description": "Branching strategies, rebase, merge, Git workflow", "skill_tags": ["Git"], "resource_type": "course"},
            {"week": 3, "title": "Docker & Containers", "description": "Dockerfiles, compose, networking, registries", "skill_tags": ["Docker"], "resource_type": "course"},
            {"week": 4, "title": "Kubernetes", "description": "Pods, deployments, services, ingress, configmaps", "skill_tags": ["Kubernetes"], "resource_type": "course"},
            {"week": 5, "title": "CI/CD Pipelines", "description": "GitHub Actions, Jenkins, automated testing & deployment", "skill_tags": ["CI/CD"], "resource_type": "course"},
            {"week": 6, "title": "Infrastructure as Code", "description": "Terraform, Ansible, configuration management", "skill_tags": ["Terraform", "Ansible"], "resource_type": "course"},
            {"week": 7, "title": "Monitoring & Alerting", "description": "Prometheus, Grafana, alert manager, logging stacks", "skill_tags": ["Monitoring"], "resource_type": "course"},
            {"week": 8, "title": "Build DevOps Pipeline", "description": "End-to-end CI/CD with monitoring and alerting", "skill_tags": ["Docker", "Kubernetes", "CI/CD"], "resource_type": "project"},
        ],
    },
    "data": {
        "title": "Data Engineer",
        "description": "Build data pipelines and infrastructure for analytics and ML.",
        "nodes": [
            {"week": 1, "title": "Advanced SQL", "description": "Window functions, CTEs, query optimization, indexing", "skill_tags": ["SQL"], "resource_type": "course"},
            {"week": 2, "title": "Python for Data", "description": "Pandas, NumPy, data cleaning, transformation", "skill_tags": ["Python"], "resource_type": "course"},
            {"week": 3, "title": "Data Warehousing", "description": "Star schema, fact/dimension tables, data modeling", "skill_tags": ["Data Warehousing"], "resource_type": "course"},
            {"week": 4, "title": "ETL Pipelines", "description": "Build ETL with Python, Apache Airflow, dbt", "skill_tags": ["ETL", "Airflow"], "resource_type": "course"},
            {"week": 5, "title": "Big Data Tools", "description": "Spark, Hadoop, distributed computing concepts", "skill_tags": ["Spark", "Big Data"], "resource_type": "course"},
            {"week": 6, "title": "Cloud Data Services", "description": "AWS Redshift, BigQuery, Snowflake, data lakes", "skill_tags": ["AWS", "Cloud"], "resource_type": "course"},
            {"week": 7, "title": "Data Pipeline Project", "description": "Build an end-to-end data pipeline", "skill_tags": ["Python", "SQL", "Airflow"], "resource_type": "project"},
            {"week": 8, "title": "Data Quality & Governance", "description": "Data validation, lineage, cataloging, governance", "skill_tags": ["Data Engineering"], "resource_type": "course"},
        ],
    },
    "pm": {
        "title": "Product Manager",
        "description": "Lead product strategy, user research, and cross-functional teams.",
        "nodes": [
            {"week": 1, "title": "Product Thinking", "description": "Product lifecycle, strategy, vision, OKRs", "skill_tags": ["Product Strategy"], "resource_type": "course"},
            {"week": 2, "title": "User Research", "description": "User interviews, surveys, personas, JTBD framework", "skill_tags": ["User Research"], "resource_type": "course"},
            {"week": 3, "title": "Product Analytics", "description": "Metrics, A/B testing, cohort analysis, funnel analysis", "skill_tags": ["Analytics"], "resource_type": "course"},
            {"week": 4, "title": "Technical Fundamentals", "description": "APIs, databases, architecture basics for PMs", "skill_tags": ["Technical"], "resource_type": "course"},
            {"week": 5, "title": "Agile & Scrum", "description": "Sprint planning, standups, retrospectives, stakeholder management", "skill_tags": ["Agile"], "resource_type": "course"},
            {"week": 6, "title": "Product Design", "description": "Wireframing, prototyping, UX principles, design sprints", "skill_tags": ["Product Design"], "resource_type": "course"},
            {"week": 7, "title": "Go-to-Market Strategy", "description": "Launch planning, positioning, messaging, pricing", "skill_tags": ["GTM Strategy"], "resource_type": "course"},
            {"week": 8, "title": "Product Portfolio Project", "description": "Create a full product plan from research to launch", "skill_tags": ["Product Management"], "resource_type": "project"},
        ],
    },
}


def generate_roadmap(user_id, category=None, target_role=None):
    """Generate a personalized learning roadmap for a user."""
    from app.career.services.career_memory_service import build_career_memory

    memory = build_career_memory(user_id)

    # Determine the best roadmap category
    if not category:
        cp = memory.get("career_profile", {})
        category = _infer_category(cp.get("target_role", ""), memory.get("skills", {}))

    if category not in ROADMAP_TEMPLATES:
        category = "fullstack"

    template = ROADMAP_TEMPLATES[category]
    title = target_role or template["title"]
    roadmap = Roadmap(
        user_id=user_id,
        title=f"{title} Learning Roadmap",
        description=template["description"],
        target_role=title,
        category=category,
        estimated_weeks=len(template["nodes"]),
        status="active",
        source="ai_generated",
    )
    db.session.add(roadmap)
    db.session.flush()

    # Add nodes
    for i, node_data in enumerate(template["nodes"]):
        node = RoadmapNode(
            roadmap_id=roadmap.id,
            title=node_data["title"],
            description=node_data.get("description", ""),
            resource_type=node_data.get("resource_type", "article"),
            order=i + 1,
            week=node_data.get("week", 1),
            status="pending",
            skill_tags=node_data.get("skill_tags", []),
        )
        db.session.add(node)

    # Create LearningProgress entries for target skills
    for node_data in template["nodes"]:
        for skill in node_data.get("skill_tags", []):
            existing = LearningProgress.query.filter_by(
                user_id=user_id, skill_name=skill
            ).first()
            if not existing:
                lp = LearningProgress(
                    user_id=user_id,
                    skill_name=skill,
                    proficiency=0,
                    category=category,
                    source="roadmap",
                )
                db.session.add(lp)

    db.session.commit()
    return get_roadmap_with_nodes(roadmap.id)


def get_roadmap_with_nodes(roadmap_id):
    """Get a roadmap with all its nodes."""
    roadmap = Roadmap.query.get(roadmap_id)
    if not roadmap:
        return None

    nodes = RoadmapNode.query.filter_by(roadmap_id=roadmap_id).order_by(RoadmapNode.order).all()
    completed = sum(1 for n in nodes if n.status == "completed")
    total = len(nodes)

    return {
        "id": roadmap.id,
        "title": roadmap.title,
        "description": roadmap.description,
        "target_role": roadmap.target_role,
        "category": roadmap.category,
        "estimated_weeks": roadmap.estimated_weeks,
        "progress": roadmap.progress or int((completed / total) * 100) if total > 0 else 0,
        "status": roadmap.status,
        "created_at": roadmap.created_at.isoformat() if roadmap.created_at else None,
        "completed_nodes": completed,
        "total_nodes": total,
        "nodes": [
            {
                "id": n.id, "title": n.title, "description": n.description,
                "resource_url": n.resource_url, "resource_type": n.resource_type,
                "order": n.order, "week": n.week, "status": n.status,
                "skill_tags": n.skill_tags or [],
                "completed_at": n.completed_at.isoformat() if n.completed_at else None,
            }
            for n in nodes
        ],
    }


def update_roadmap_progress(user_id, node_id, status):
    """Mark a roadmap node as completed/in_progress and update roadmap progress."""
    node = RoadmapNode.query.get(node_id)
    if not node:
        return None

    roadmap = Roadmap.query.get(node.roadmap_id)
    if not roadmap or roadmap.user_id != user_id:
        return None

    if status == "completed" and node.status != "completed":
        node.status = "completed"
        node.completed_at = datetime.now(timezone.utc)
    elif status == "in_progress" and node.status == "pending":
        node.status = "in_progress"
    else:
        node.status = status

    # Update roadmap progress
    nodes = RoadmapNode.query.filter_by(roadmap_id=roadmap.id).all()
    completed = sum(1 for n in nodes if n.status == "completed")
    total = len(nodes)
    roadmap.progress = int((completed / total) * 100) if total > 0 else 0

    # Update LearningProgress for skill tags
    if status == "completed":
        for skill in (node.skill_tags or []):
            lp = LearningProgress.query.filter_by(
                user_id=user_id, skill_name=skill
            ).first()
            if lp:
                lp.proficiency = min(100, lp.proficiency + 20)
            else:
                lp = LearningProgress(
                    user_id=user_id, skill_name=skill,
                    proficiency=20, category=roadmap.category, source="roadmap",
                )
                db.session.add(lp)

    db.session.commit()

    if roadmap.status == "active" and roadmap.progress == 100:
        roadmap.status = "completed"
        db.session.commit()

    return get_roadmap_with_nodes(roadmap.id)


def _infer_category(target_role, skills_data):
    """Infer a roadmap category from the user's target role and skills."""
    role_lower = target_role.lower() if target_role else ""
    if any(w in role_lower for w in ["backend", "api", "server"]):
        return "backend"
    elif any(w in role_lower for w in ["frontend", "ui", "react", "web"]):
        return "frontend"
    elif any(w in role_lower for w in ["full", "fullstack", "full-stack"]):
        return "fullstack"
    elif any(w in role_lower for w in ["ai", "machine learning", "ml", "deep learning"]):
        return "ai"
    elif any(w in role_lower for w in ["cyber", "security", "sec"]):
        return "cybersecurity"
    elif any(w in role_lower for w in ["cloud", "aws", "azure", "gcp"]):
        return "cloud"
    elif any(w in role_lower for w in ["devops", "sre", "platform"]):
        return "devops"
    elif any(w in role_lower for w in ["data", "analytics", "data engineer"]):
        return "data"
    elif any(w in role_lower for w in ["product", "pm"]):
        return "pm"

    # Infer from skills
    resume_skills = skills_data.get("resume_skills", []) if isinstance(skills_data, dict) else []
    skill_lower = [s.lower() for s in resume_skills]
    if any(s in skill_lower for s in ["react", "vue", "angular", "css", "html", "javascript"]):
        if any(s in skill_lower for s in ["flask", "django", "node", "express", "sql"]):
            return "fullstack"
        return "frontend"
    if any(s in skill_lower for s in ["flask", "django", "python", "sql", "postgresql"]):
        return "backend"

    return "fullstack"
