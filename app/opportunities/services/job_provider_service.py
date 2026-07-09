import logging
from datetime import datetime, timezone
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ProviderBase(ABC):
    @abstractmethod
    def search(self, query: str, location: Optional[str] = None, **kwargs) -> list[dict]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class ProviderRegistry:
    _providers: dict[str, ProviderBase] = {}

    @classmethod
    def register(cls, provider: ProviderBase):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[ProviderBase]:
        return cls._providers.get(name)

    @classmethod
    def all(cls) -> list[ProviderBase]:
        return list(cls._providers.values())


def search_providers(query: str, location: Optional[str] = None, providers: Optional[list[str]] = None, **kwargs) -> list[dict]:
    results = []
    targets = [ProviderRegistry.get(p) for p in providers] if providers else ProviderRegistry.all()
    for provider in targets:
        if provider:
            try:
                results.extend(provider.search(query, location=location, **kwargs))
            except Exception as e:
                logger.error("Provider %s search failed: %s", provider.name, e)
    return results


SAMPLE_OPPORTUNITIES = [
    {
        "title": "Senior Backend Engineer",
        "company_name": "Google",
        "company_logo": "https://logo.clearbit.com/google.com",
        "company_url": "https://google.com",
        "location": "Bangalore, India",
        "remote_type": "hybrid",
        "salary_min": 1800000,
        "salary_max": 3500000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 4,
        "experience_max": 8,
        "description": "Build and scale distributed systems powering Google's core products. Work on high-throughput low-latency services serving billions of users.",
        "requirements": [
            "Strong Python or Go skills",
            "Experience with distributed systems",
            "Deep understanding of data structures and algorithms",
            "Experience with cloud infrastructure (GCP preferred)",
        ],
        "responsibilities": [
            "Design and implement scalable backend services",
            "Optimize system performance and reliability",
            "Collaborate with cross-functional teams",
            "Mentor junior engineers",
        ],
        "tech_stack": ["Python", "Go", "GCP", "Bigtable", "Spanner", "Pub/Sub", "gRPC"],
        "provider": "sample",
    },
    {
        "title": "Full Stack Developer",
        "company_name": "Microsoft",
        "company_logo": "https://logo.clearbit.com/microsoft.com",
        "company_url": "https://microsoft.com",
        "location": "Hyderabad, India",
        "remote_type": "hybrid",
        "salary_min": 1500000,
        "salary_max": 2800000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 2,
        "experience_max": 6,
        "description": "Join Microsoft's Azure Cloud team to build next-generation developer tools and cloud services used by millions.",
        "requirements": [
            "Proficiency in TypeScript and React",
            "Experience with Node.js or C#",
            "Understanding of cloud computing concepts",
            "Familiarity with agile development",
        ],
        "responsibilities": [
            "Develop cloud-based applications and services",
            "Build responsive UIs with React",
            "Write comprehensive tests",
            "Participate in code reviews",
        ],
        "tech_stack": ["TypeScript", "React", "Node.js", "Azure", "C#", "SQL Server"],
        "provider": "sample",
    },
    {
        "title": "Machine Learning Engineer",
        "company_name": "Amazon",
        "company_logo": "https://logo.clearbit.com/amazon.com",
        "company_url": "https://amazon.com",
        "location": "Bangalore, India",
        "remote_type": "on-site",
        "salary_min": 2000000,
        "salary_max": 4000000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 3,
        "experience_max": 7,
        "description": "Build ML models that power Amazon's recommendation systems, search, and personalization at global scale.",
        "requirements": [
            "Strong Python and ML framework skills",
            "Experience with recommendation systems",
            "Understanding of NLP and deep learning",
            "Experience with large-scale data processing",
        ],
        "responsibilities": [
            "Design and train ML models at scale",
            "Optimize model inference for production",
            "Analyze experiment results",
            "Collaborate with research teams",
        ],
        "tech_stack": ["Python", "PyTorch", "TensorFlow", "AWS SageMaker", "Spark", "Kafka"],
        "provider": "sample",
    },
    {
        "title": "Frontend Engineer",
        "company_name": "Flipkart",
        "company_logo": "https://logo.clearbit.com/flipkart.com",
        "company_url": "https://flipkart.com",
        "location": "Bangalore, India",
        "remote_type": "on-site",
        "salary_min": 1200000,
        "salary_max": 2400000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 1,
        "experience_max": 4,
        "description": "Build world-class e-commerce experiences for millions of Indian shoppers across web and mobile web.",
        "requirements": [
            "Strong React and JavaScript skills",
            "Experience with state management",
            "Understanding of web performance optimization",
            "Familiarity with responsive design",
        ],
        "responsibilities": [
            "Build and maintain frontend features",
            "Optimize page load performance",
            "Implement A/B experiments",
            "Contribute to design system",
        ],
        "tech_stack": ["React", "JavaScript", "TypeScript", "Redux", "Node.js", "Webpack"],
        "provider": "sample",
    },
    {
        "title": "DevOps Engineer",
        "company_name": "Swiggy",
        "company_logo": "https://logo.clearbit.com/swiggy.com",
        "company_url": "https://swiggy.com",
        "location": "Bangalore, India",
        "remote_type": "hybrid",
        "salary_min": 1400000,
        "salary_max": 2600000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 2,
        "experience_max": 5,
        "description": "Manage and scale Swiggy's cloud infrastructure serving millions of daily food delivery orders across India.",
        "requirements": [
            "Experience with AWS or GCP",
            "Strong Kubernetes and Docker skills",
            "Infrastructure as Code experience",
            "Monitoring and observability expertise",
        ],
        "responsibilities": [
            "Manage Kubernetes clusters at scale",
            "Automate infrastructure provisioning",
            "Improve system reliability and uptime",
            "Lead incident response",
        ],
        "tech_stack": ["AWS", "Kubernetes", "Docker", "Terraform", "Prometheus", "Grafana"],
        "provider": "sample",
    },
    {
        "title": "Backend Intern",
        "company_name": "Razorpay",
        "company_logo": "https://logo.clearbit.com/razorpay.com",
        "company_url": "https://razorpay.com",
        "location": "Bangalore, India",
        "remote_type": "on-site",
        "salary_min": 400000,
        "salary_max": 800000,
        "currency": "INR",
        "employment_type": "internship",
        "experience_required": 0,
        "experience_max": 1,
        "description": "Join Razorpay's engineering team to build payment infrastructure that powers millions of Indian businesses.",
        "requirements": [
            "Basic knowledge of Python or Go",
            "Understanding of REST APIs",
            "Familiarity with SQL databases",
            "Eagerness to learn",
        ],
        "responsibilities": [
            "Build and maintain API endpoints",
            "Write unit and integration tests",
            "Fix bugs and improve documentation",
            "Learn from senior engineers",
        ],
        "tech_stack": ["Python", "Django", "PostgreSQL", "Redis", "Docker"],
        "provider": "sample",
    },
    {
        "title": "Data Scientist",
        "company_name": "Uber",
        "company_logo": "https://logo.clearbit.com/uber.com",
        "company_url": "https://uber.com",
        "location": "Remote, India",
        "remote_type": "remote",
        "salary_min": 1600000,
        "salary_max": 3000000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 2,
        "experience_max": 6,
        "description": "Use data to solve complex problems in ride-sharing, delivery, and mobility at global scale.",
        "requirements": [
            "Strong SQL and Python skills",
            "Experience with statistical analysis",
            "Understanding of A/B testing",
            "Data visualization expertise",
        ],
        "responsibilities": [
            "Analyze large datasets to drive product decisions",
            "Design and analyze A/B experiments",
            "Build dashboards and reports",
            "Present findings to stakeholders",
        ],
        "tech_stack": ["Python", "SQL", "Spark", "Tableau", "Airflow", "Hive"],
        "provider": "sample",
    },
    {
        "title": "Product Designer",
        "company_name": "Notion",
        "company_logo": "https://logo.clearbit.com/notion.so",
        "company_url": "https://notion.so",
        "location": "Remote, India",
        "remote_type": "remote",
        "salary_min": 1200000,
        "salary_max": 2500000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 2,
        "experience_max": 5,
        "description": "Design intuitive, powerful interfaces that help millions of people organize their work and lives.",
        "requirements": [
            "Strong portfolio showing UX/UI work",
            "Experience with Figma",
            "Understanding of design systems",
            "User research experience",
        ],
        "responsibilities": [
            "Design new features end-to-end",
            "Maintain and evolve design system",
            "Conduct user research",
            "Collaborate with engineering",
        ],
        "tech_stack": ["Figma", "Prototyping", "User Research", "Design Systems"],
        "provider": "sample",
    },
    {
        "title": "Software Development Engineer",
        "company_name": "Zomato",
        "company_logo": "https://logo.clearbit.com/zomato.com",
        "company_url": "https://zomato.com",
        "location": "Gurgaon, India",
        "remote_type": "on-site",
        "salary_min": 1300000,
        "salary_max": 2500000,
        "currency": "INR",
        "employment_type": "full-time",
        "experience_required": 1,
        "experience_max": 4,
        "description": "Build technology that powers food delivery for millions of users across India and international markets.",
        "requirements": [
            "Proficiency in Go or Java",
            "Experience with microservices",
            "Understanding of distributed systems",
            "Problem-solving skills",
        ],
        "responsibilities": [
            "Develop and deploy microservices",
            "Optimize system performance",
            "Participate in architecture discussions",
            "Write clean, tested code",
        ],
        "tech_stack": ["Go", "Java", "PostgreSQL", "Kafka", "Redis", "Docker"],
        "provider": "sample",
    },
    {
        "title": "AI Research Intern",
        "company_name": "Google Research",
        "company_logo": "https://logo.clearbit.com/google.com",
        "company_url": "https://research.google",
        "location": "Bangalore, India",
        "remote_type": "on-site",
        "salary_min": 600000,
        "salary_max": 1200000,
        "currency": "INR",
        "employment_type": "internship",
        "experience_required": 0,
        "experience_max": 1,
        "description": "Work on cutting-edge AI research problems with world-class researchers at Google Research India.",
        "requirements": [
            "Pursuing MTech/PhD in ML/AI",
            "Strong Python and research skills",
            "Published papers preferred",
            "Deep learning framework experience",
        ],
        "responsibilities": [
            "Conduct novel AI research",
            "Implement and evaluate models",
            "Write research papers",
            "Collaborate with research team",
        ],
        "tech_stack": ["Python", "JAX", "TensorFlow", "PyTorch", "Google Cloud"],
        "provider": "sample",
    },
]


def seed_sample_opportunities():
    from app.extensions import db
    from app.opportunities.models import Opportunity

    existing = Opportunity.query.first()
    if existing:
        logger.info("Sample opportunities already seeded, skipping")
        return

    count = 0
    for data in SAMPLE_OPPORTUNITIES:
        tech_stack = data.pop("tech_stack", [])
        opp = Opportunity(**data, tech_stack=tech_stack, is_active=True, scraped_at=datetime.now(timezone.utc))
        db.session.add(opp)
        count += 1

    db.session.commit()
    logger.info("Seeded %d sample opportunities", count)
