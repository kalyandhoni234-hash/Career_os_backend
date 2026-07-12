from dataclasses import dataclass, field


@dataclass
class SkillInfo:
    name: str
    tier: str  # "core", "intermediate", "advanced"
    priority: int  # 1-5 (5=critical)
    reason: str
    learning_time_weeks: int
    resources: list[str] = field(default_factory=list)
    unlocks: list[str] = field(default_factory=list)
    ats_gain: int = 3


@dataclass
class RoleSkillMap:
    title: str
    aliases: list[str]
    description: str
    skills: dict[str, SkillInfo]
    estimated_months: int = 12


ROLE_SKILL_MAPS: dict[str, RoleSkillMap] = {}

# ──────────────────────────────────────────────
# Ethical Hacker / Penetration Tester
# ──────────────────────────────────────────────
_ethical_hacker = RoleSkillMap(
    title="Ethical Hacker",
    aliases=[
        "ethical hacker",
        "penetration tester",
        "pentester",
        "cybersecurity engineer",
        "cybersecurity analyst",
        "security engineer",
        "security analyst",
        "offensive security",
        "red team",
    ],
    description="Identifies and exploits vulnerabilities in systems, networks, and applications to help organizations fix security flaws before malicious actors can exploit them.",
    estimated_months=14,
    skills={
        "networking": SkillInfo(
            name="networking",
            tier="core",
            priority=5,
            reason="Every attack vector travels over a network; understanding TCP/IP, DNS, HTTP/S, and routing is prerequisite to all security work",
            learning_time_weeks=4,
            resources=[
                "Professor Messer Network+ (free)",
                "CompTIA Network+ Study Guide",
            ],
            unlocks=["network scanning", "packet analysis", "firewall evasion"],
            ats_gain=8,
        ),
        "linux": SkillInfo(
            name="linux",
            tier="core",
            priority=5,
            reason="Most servers, security tools, and target environments run Linux; command-line fluency is non-negotiable",
            learning_time_weeks=6,
            resources=[
                "Linux Journey (linuxjourney.com)",
                "OverTheWire Bandit wargame",
            ],
            unlocks=["bash scripting", "privilege escalation", "log analysis"],
            ats_gain=7,
        ),
        "web application security": SkillInfo(
            name="web application security",
            tier="core",
            priority=5,
            reason="OWASP Top 10 vulnerabilities (SQLi, XSS, CSRF, SSRF) are the most common entry points in modern pentesting engagements",
            learning_time_weeks=6,
            resources=[
                "PortSwigger Web Security Academy",
                "OWASP Top 10 (owasp.org)",
            ],
            unlocks=["bug bounty hunting", "secure code review"],
            ats_gain=9,
        ),
        "penetration testing methodology": SkillInfo(
            name="penetration testing methodology",
            tier="core",
            priority=5,
            reason="Structured approach (reconnaissance → scanning → exploitation → post-exploitation → reporting) is what separates professional pentesters from script kiddies",
            learning_time_weeks=4,
            resources=[
                "PTES (Penetration Testing Execution Standard)",
                "OSCP course materials",
            ],
            unlocks=["professional certification", "client reporting"],
            ats_gain=9,
        ),
        "vulnerability assessment": SkillInfo(
            name="vulnerability assessment",
            tier="core",
            priority=5,
            reason="Finding and prioritizing vulnerabilities is the primary deliverable of security roles; requires knowledge of CVSS, CVE, and scanning tools",
            learning_time_weeks=3,
            resources=[
                "NVD (nvd.nist.gov)",
                "Tenable Nessus essentials",
            ],
            unlocks=["risk management", "compliance frameworks"],
            ats_gain=8,
        ),
        "bash scripting": SkillInfo(
            name="bash scripting",
            tier="intermediate",
            priority=4,
            reason="Automates reconnaissance, log parsing, and exploit chaining; essential for efficient pentesting workflows",
            learning_time_weeks=3,
            resources=[
                "Shell Scripting Tutorial (shellscript.sh)",
            ],
            unlocks=["automation", "tool customization"],
            ats_gain=5,
        ),
        "python": SkillInfo(
            name="python",
            tier="intermediate",
            priority=4,
            reason="Used for writing custom exploits, fuzzers, and automation scripts; most security tools provide Python bindings",
            learning_time_weeks=4,
            resources=[
                "Black Hat Python (book)",
                "Automate the Boring Stuff",
            ],
            unlocks=["exploit development", "custom tooling"],
            ats_gain=6,
        ),
        "nmap": SkillInfo(
            name="nmap",
            tier="intermediate",
            priority=4,
            reason="The industry-standard network scanning tool for host discovery, port scanning, and service/OS fingerprinting",
            learning_time_weeks=2,
            resources=[
                "Nmap Network Scanning (official guide)",
            ],
            unlocks=["network mapping", "service enumeration"],
            ats_gain=6,
        ),
        "burp suite": SkillInfo(
            name="burp suite",
            tier="intermediate",
            priority=4,
            reason="The most widely used web application proxy for intercepting, modifying, and replaying HTTP traffic during web app pentests",
            learning_time_weeks=3,
            resources=[
                "PortSwiger Burp Suite documentation",
            ],
            unlocks=["web app pentesting", "session manipulation"],
            ats_gain=6,
        ),
        "wireshark": SkillInfo(
            name="wireshark",
            tier="intermediate",
            priority=4,
            reason="Packet-level analysis is essential for understanding network protocols, diagnosing issues, and finding indicators of compromise",
            learning_time_weeks=2,
            resources=[
                "Wireshark University (wireshark.org)",
                "Chris Greer's packet analysis videos",
            ],
            unlocks=["traffic analysis", "forensics"],
            ats_gain=5,
        ),
        "metasploit": SkillInfo(
            name="metasploit",
            tier="intermediate",
            priority=4,
            reason="The most popular exploitation framework; provides ready-made exploits, payloads, and post-exploitation modules",
            learning_time_weeks=3,
            resources=[
                "Metasploit Unleashed (offensive-security.com)",
            ],
            unlocks=["exploitation", "payload generation"],
            ats_gain=6,
        ),
        "sql injection": SkillInfo(
            name="sql injection",
            tier="intermediate",
            priority=4,
            reason="One of the most critical and common web vulnerabilities; understanding manual and automated SQLi techniques is essential",
            learning_time_weeks=3,
            resources=[
                "PortSwiger SQLi cheat sheet",
            ],
            unlocks=["database exploitation", "data exfiltration"],
            ats_gain=7,
        ),
        "cryptography": SkillInfo(
            name="cryptography",
            tier="advanced",
            priority=3,
            reason="Understanding encryption algorithms, hashing, PKI, and common cryptographic flaws is needed for advanced security assessments",
            learning_time_weeks=6,
            resources=[
                "Coursera Cryptography I (Dan Boneh)",
            ],
            unlocks=["protocol analysis", "secure architecture"],
            ats_gain=4,
        ),
        "reverse engineering": SkillInfo(
            name="reverse engineering",
            tier="advanced",
            priority=3,
            reason="Needed to analyze malware, find vulnerabilities in binaries, and understand proprietary protocols",
            learning_time_weeks=8,
            resources=[
                "Practical Malware Analysis (book)",
                "Ghidra / IDA Pro tutorials",
            ],
            unlocks=["malware analysis", "0-day discovery"],
            ats_gain=4,
        ),
        "malware analysis": SkillInfo(
            name="malware analysis",
            tier="advanced",
            priority=3,
            reason="Essential for incident response and understanding attacker TTPs; combines reverse engineering with behavioral analysis",
            learning_time_weeks=8,
            resources=[
                "Practical Malware Analysis (book)",
                "ANY.RUN sandbox tutorials",
            ],
            unlocks=["incident response", "threat intelligence"],
            ats_gain=4,
        ),
        "cloud security": SkillInfo(
            name="cloud security",
            tier="advanced",
            priority=3,
            reason="As organizations migrate to cloud, knowledge of AWS/Azure/GCP security configurations and common misconfigurations is increasingly important",
            learning_time_weeks=6,
            resources=[
                "AWS Security Specialty materials",
                "Pacu (cloud exploitation framework)",
            ],
            unlocks=["cloud pentesting", "DevSecOps"],
            ats_gain=5,
        ),
        "exploit development": SkillInfo(
            name="exploit development",
            tier="advanced",
            priority=3,
            reason="Writing custom exploits (buffer overflows, ROP chains, etc.) is required for advanced pentesting and 0-day research",
            learning_time_weeks=10,
            resources=[
                "Corelan Exploit Writing tutorials",
                "The Shellcoder's Handbook",
            ],
            unlocks=["0-day discovery", "OSCP/OSCE certifications"],
            ats_gain=3,
        ),
        "digital forensics": SkillInfo(
            name="digital forensics",
            tier="advanced",
            priority=2,
            reason="Understanding how to collect, preserve, and analyze digital evidence is important for incident response and legal proceedings",
            learning_time_weeks=6,
            resources=[
                "SANS FOR500 materials",
                "Autopsy / FTK tutorials",
            ],
            unlocks=["incident response", "e-discovery"],
            ats_gain=3,
        ),
        "social engineering": SkillInfo(
            name="social engineering",
            tier="advanced",
            priority=2,
            reason="Human factors are often the weakest link; understanding phishing, pretexting, and physical security assessments broadens testing capability",
            learning_time_weeks=3,
            resources=[
                "Social Engineering: The Art of Human Hacking (book)",
                "SET (Social Engineering Toolkit)",
            ],
            unlocks=["phishing campaigns", "physical security assessments"],
            ats_gain=3,
        ),
    },
)
ROLE_SKILL_MAPS["ethical hacker"] = _ethical_hacker


# ──────────────────────────────────────────────
# Full Stack Developer
# ──────────────────────────────────────────────
_full_stack = RoleSkillMap(
    title="Full Stack Developer",
    aliases=[
        "full stack developer",
        "full stack engineer",
        "fullstack developer",
        "fullstack engineer",
        "web developer",
        "web engineer",
    ],
    description="Builds end-to-end web applications — frontend UI, backend APIs, databases, and deployment — shipping features from concept to production.",
    estimated_months=12,
    skills={
        "html": SkillInfo(
            name="html",
            tier="core",
            priority=5,
            reason="The foundational markup language of the web; every frontend starts here",
            learning_time_weeks=2,
            resources=[
                "MDN HTML docs",
            ],
            unlocks=["css", "javascript dom"],
            ats_gain=4,
        ),
        "css": SkillInfo(
            name="css",
            tier="core",
            priority=5,
            reason="Controls layout, responsiveness, and visual design; essential for building user-facing interfaces",
            learning_time_weeks=4,
            resources=[
                "MDN CSS docs",
                "CSS Tricks",
            ],
            unlocks=["tailwind", "bootstrap", "responsive design"],
            ats_gain=4,
        ),
        "javascript": SkillInfo(
            name="javascript",
            tier="core",
            priority=5,
            reason="The universal language of the browser; required for all frontend and Node.js backend work",
            learning_time_weeks=8,
            resources=[
                "MDN JavaScript Guide",
                "You Don't Know JS (book series)",
            ],
            unlocks=["react", "node.js", "typescript"],
            ats_gain=9,
        ),
        "react": SkillInfo(
            name="react",
            tier="core",
            priority=5,
            reason="The most popular frontend framework; used by most modern web applications for building interactive UIs",
            learning_time_weeks=8,
            resources=[
                "React.dev official tutorial",
            ],
            unlocks=["next.js", "react native", "state management"],
            ats_gain=9,
        ),
        "rest apis": SkillInfo(
            name="rest apis",
            tier="core",
            priority=5,
            reason="The standard pattern for communication between frontend and backend; every full stack app relies on APIs",
            learning_time_weeks=3,
            resources=[
                "REST API Tutorial (restapitutorial.com)",
            ],
            unlocks=["backend development", "integration patterns"],
            ats_gain=7,
        ),
        "sql": SkillInfo(
            name="sql",
            tier="core",
            priority=5,
            reason="Relational databases power most applications; querying, joins, indexing, and schema design are daily tasks",
            learning_time_weeks=5,
            resources=[
                "SQLZoo (sqlzoo.net)",
                "PostgreSQL Tutorial",
            ],
            unlocks=["postgresql", "database design", "data analysis"],
            ats_gain=7,
        ),
        "git": SkillInfo(
            name="git",
            tier="core",
            priority=5,
            reason="Version control is the backbone of collaborative development; branching, merging, and PR workflows are used daily",
            learning_time_weeks=2,
            resources=[
                "Pro Git (book)",
            ],
            unlocks=["ci/cd", "team collaboration"],
            ats_gain=5,
        ),
        "node.js": SkillInfo(
            name="node.js",
            tier="core",
            priority=5,
            reason="JavaScript runtime for backend development; enables full-stack JavaScript and is required for most modern web frameworks",
            learning_time_weeks=5,
            resources=[
                "Node.js official docs",
                "The Odin Project Node.js path",
            ],
            unlocks=["express", "next.js", "serverless functions"],
            ats_gain=8,
        ),
        "postgresql": SkillInfo(
            name="postgresql",
            tier="core",
            priority=4,
            reason="The most advanced and popular open-source relational database; used in production by startups and enterprises alike",
            learning_time_weeks=4,
            resources=[
                "PostgreSQL Tutorial (postgresqltutorial.com)",
            ],
            unlocks=["database optimization", "data modeling"],
            ats_gain=6,
        ),
        "typescript": SkillInfo(
            name="typescript",
            tier="intermediate",
            priority=4,
            reason="Adds static typing to JavaScript, catching bugs at compile time; increasingly required by modern codebases",
            learning_time_weeks=4,
            resources=[
                "TypeScript Handbook (typescriptlang.org)",
            ],
            unlocks=["type-safe react", "large-scale applications"],
            ats_gain=6,
        ),
        "testing": SkillInfo(
            name="testing",
            tier="intermediate",
            priority=4,
            reason="Unit, integration, and e2e testing ensures code quality and prevents regressions; a key differentiator for professional developers",
            learning_time_weeks=4,
            resources=[
                "Testing Library docs",
                "Cypress docs",
            ],
            unlocks=["jest", "cypress", "playwright", "tdd"],
            ats_gain=5,
        ),
        "next.js": SkillInfo(
            name="next.js",
            tier="intermediate",
            priority=4,
            reason="The dominant React framework with SSR, SSG, routing, and server components; used by most production React applications",
            learning_time_weeks=4,
            resources=[
                "Next.js docs (nextjs.org)",
            ],
            unlocks=["full-stack react", "ssr", "seo optimization"],
            ats_gain=7,
        ),
        "tailwind css": SkillInfo(
            name="tailwind css",
            tier="intermediate",
            priority=4,
            reason="Utility-first CSS framework that dramatically speeds up UI development and enforces design consistency",
            learning_time_weeks=2,
            resources=[
                "Tailwind CSS docs",
            ],
            unlocks=["rapid prototyping", "responsive design"],
            ats_gain=4,
        ),
        "docker": SkillInfo(
            name="docker",
            tier="intermediate",
            priority=4,
            reason="Containerization is the standard for consistent development environments, testing, and deployment",
            learning_time_weeks=3,
            resources=[
                "Docker Get Started guide",
            ],
            unlocks=["ci/cd", "container orchestration", "microservices"],
            ats_gain=6,
        ),
        "ci/cd": SkillInfo(
            name="ci/cd",
            tier="intermediate",
            priority=3,
            reason="Automation of testing, building, and deployment pipelines is essential for modern software delivery",
            learning_time_weeks=3,
            resources=[
                "GitHub Actions docs",
            ],
            unlocks=["devops", "automated deployment"],
            ats_gain=4,
        ),
        "graphql": SkillInfo(
            name="graphql",
            tier="advanced",
            priority=2,
            reason="Flexible API query language that reduces over-fetching and enables efficient client-driven data fetching",
            learning_time_weeks=3,
            resources=[
                "GraphQL.org learn section",
            ],
            unlocks=["apollo", "real-time subscriptions"],
            ats_gain=3,
        ),
        "redis": SkillInfo(
            name="redis",
            tier="advanced",
            priority=2,
            reason="In-memory data store used for caching, session management, and real-time features; improves application performance",
            learning_time_weeks=2,
            resources=[
                "Redis University (redis.io)",
            ],
            unlocks=["caching strategies", "rate limiting"],
            ats_gain=3,
        ),
        "cloud": SkillInfo(
            name="cloud",
            tier="advanced",
            priority=2,
            reason="Understanding cloud platforms (AWS/GCP/Azure) for deployment, storage, and serverless functions rounds out full-stack capability",
            learning_time_weeks=6,
            resources=[
                "AWS Cloud Practitioner Essentials",
            ],
            unlocks=["serverless", "cloud infrastructure"],
            ats_gain=4,
        ),
        "system design": SkillInfo(
            name="system design",
            tier="advanced",
            priority=2,
            reason="Architecture, scaling, load balancing, and microservices knowledge is needed for senior-level roles and technical interviews",
            learning_time_weeks=8,
            resources=[
                "System Design Interview (Alex Xu)",
            ],
            unlocks=["architect roles", "tech lead"],
            ats_gain=3,
        ),
        "prisma": SkillInfo(
            name="prisma",
            tier="intermediate",
            priority=3,
            reason="Modern ORM that simplifies database access with type-safe queries and migrations; widely adopted in full-stack TypeScript projects",
            learning_time_weeks=2,
            resources=[
                "Prisma docs",
            ],
            unlocks=["type-safe database access", "rapid backend development"],
            ats_gain=4,
        ),
    },
)
ROLE_SKILL_MAPS["full stack developer"] = _full_stack


# ──────────────────────────────────────────────
# AI Engineer
# ──────────────────────────────────────────────
_ai_engineer = RoleSkillMap(
    title="AI Engineer",
    aliases=[
        "ai engineer",
        "ai/ml engineer",
        "machine learning engineer",
        "ml engineer",
        "ai developer",
    ],
    description="Designs, trains, deploys, and maintains machine learning models and AI systems — from classical ML to large language models and generative AI.",
    estimated_months=14,
    skills={
        "python": SkillInfo(
            name="python",
            tier="core",
            priority=5,
            reason="The lingua franca of AI/ML; all major frameworks (PyTorch, TensorFlow, scikit-learn) and data tools (pandas, numpy) are Python-first",
            learning_time_weeks=6,
            resources=[
                "Python.org official tutorial",
            ],
            unlocks=["pytorch", "pandas", "ml libraries"],
            ats_gain=9,
        ),
        "machine learning": SkillInfo(
            name="machine learning",
            tier="core",
            priority=5,
            reason="Fundamental understanding of supervised/unsupervised learning, model evaluation, and feature engineering is the foundation of all AI work",
            learning_time_weeks=10,
            resources=[
                "Andrew Ng's Machine Learning course (Coursera)",
            ],
            unlocks=["deep learning", "nlp", "computer vision"],
            ats_gain=9,
        ),
        "pytorch": SkillInfo(
            name="pytorch",
            tier="core",
            priority=5,
            reason="The most widely used deep learning framework in both research and production; dynamic computation graphs make it intuitive and flexible",
            learning_time_weeks=6,
            resources=[
                "PyTorch official tutorials",
            ],
            unlocks=["transformers", "custom architectures", "distributed training"],
            ats_gain=8,
        ),
        "pandas": SkillInfo(
            name="pandas",
            tier="core",
            priority=5,
            reason="The essential data manipulation library for loading, cleaning, transforming, and exploring tabular data before modeling",
            learning_time_weeks=3,
            resources=[
                "Pandas documentation (pandas.pydata.org)",
            ],
            unlocks=["data analysis", "feature engineering"],
            ats_gain=7,
        ),
        "numpy": SkillInfo(
            name="numpy",
            tier="core",
            priority=5,
            reason="The numerical computing backbone of the Python ML ecosystem; all frameworks build on numpy arrays for efficient computation",
            learning_time_weeks=2,
            resources=[
                "NumPy quickstart",
            ],
            unlocks=["linear algebra ops", "array computing"],
            ats_gain=7,
        ),
        "sql": SkillInfo(
            name="sql",
            tier="core",
            priority=4,
            reason="Most real-world data lives in databases; querying, joining, and aggregating data is necessary for data preparation and feature extraction",
            learning_time_weeks=4,
            resources=[
                "SQLZoo (sqlzoo.net)",
            ],
            unlocks=["data extraction", "feature stores"],
            ats_gain=6,
        ),
        "git": SkillInfo(
            name="git",
            tier="core",
            priority=4,
            reason="Version control for code, notebooks, and experiment configurations; essential for collaborative ML projects",
            learning_time_weeks=2,
            resources=[
                "Pro Git (book)",
            ],
            unlocks=["experiment tracking", "collaboration"],
            ats_gain=4,
        ),
        "mathematics": SkillInfo(
            name="mathematics",
            tier="core",
            priority=5,
            reason="Linear algebra, calculus, probability, and statistics underpin all ML algorithms; understanding them is required to debug and improve models",
            learning_time_weeks=12,
            resources=[
                "3Blue1Brown Essence of Linear Algebra/Calculus",
                "Introduction to Statistical Learning (ISLR)",
            ],
            unlocks=["deep learning theory", "advanced ml", "research"],
            ats_gain=7,
        ),
        "natural language processing": SkillInfo(
            name="natural language processing",
            tier="intermediate",
            priority=4,
            reason="NLP powers chatbots, search, sentiment analysis, and LLMs; understanding tokenization, embeddings, attention, and transformer architectures is essential",
            learning_time_weeks=8,
            resources=[
                "Hugging Face NLP course",
                "Stanford CS224n",
            ],
            unlocks=["llms", "rag", "text generation"],
            ats_gain=7,
        ),
        "deep learning": SkillInfo(
            name="deep learning",
            tier="intermediate",
            priority=4,
            reason="Neural network architectures (CNNs, RNNs, transformers, GANs) are the foundation of modern AI systems",
            learning_time_weeks=8,
            resources=[
                "Deep Learning Specialization (Andrew Ng)",
                "Fast.ai Practical Deep Learning",
            ],
            unlocks=["nlp", "computer vision", "generative ai"],
            ats_gain=8,
        ),
        "scikit-learn": SkillInfo(
            name="scikit-learn",
            tier="intermediate",
            priority=4,
            reason="The standard library for classical ML algorithms, preprocessing, and model evaluation; used for baselines and production pipelines",
            learning_time_weeks=3,
            resources=[
                "Scikit-learn documentation",
            ],
            unlocks=["classical ml", "model evaluation"],
            ats_gain=6,
        ),
        "mlops": SkillInfo(
            name="mlops",
            tier="intermediate",
            priority=4,
            reason="Model deployment, monitoring, versioning, and pipeline automation are required to put ML into production",
            learning_time_weeks=6,
            resources=[
                "Made With ML MLOps course",
            ],
            unlocks=["model deployment", "ml pipelines", "a/b testing"],
            ats_gain=6,
        ),
        "docker": SkillInfo(
            name="docker",
            tier="intermediate",
            priority=3,
            reason="Containerization ensures reproducible environments for training and serving models across development and production",
            learning_time_weeks=2,
            resources=[
                "Docker Get Started guide",
            ],
            unlocks=["model serving", "ml pipelines"],
            ats_gain=4,
        ),
        "llm": SkillInfo(
            name="llm",
            tier="advanced",
            priority=4,
            reason="Large language models (GPT, Llama, Mistral) are transforming AI; understanding prompting, fine-tuning, and RAG is increasingly required",
            learning_time_weeks=6,
            resources=[
                "Hugging Face Transformers course",
                "Andrej Karpathy's 'Intro to LLMs'",
            ],
            unlocks=["rag", "chatbots", "agents"],
            ats_gain=8,
        ),
        "computer vision": SkillInfo(
            name="computer vision",
            tier="advanced",
            priority=3,
            reason="Image classification, detection, segmentation, and generation are increasingly demanded in real-world AI applications",
            learning_time_weeks=8,
            resources=[
                "Stanford CS231n",
            ],
            unlocks=["object detection", "image generation"],
            ats_gain=4,
        ),
        "cloud ml services": SkillInfo(
            name="cloud ml services",
            tier="advanced",
            priority=3,
            reason="Platforms like SageMaker, Vertex AI, and Azure ML manage infrastructure for training and serving at scale",
            learning_time_weeks=4,
            resources=[
                "AWS SageMaker docs",
            ],
            unlocks=["production ml", "scaled training"],
            ats_gain=4,
        ),
        "experiment tracking": SkillInfo(
            name="experiment tracking",
            tier="advanced",
            priority=3,
            reason="Tools like MLflow, Weights & Biases, and TensorBoard are essential for logging, comparing, and reproducing ML experiments",
            learning_time_weeks=2,
            resources=[
                "MLflow docs",
                "Weights & Biases quickstart",
            ],
            unlocks=["hyperparameter tuning", "model registry"],
            ats_gain=4,
        ),
        "data engineering": SkillInfo(
            name="data engineering",
            tier="advanced",
            priority=2,
            reason="ETL pipelines, feature stores, and data warehousing are needed to feed production ML systems with reliable data",
            learning_time_weeks=6,
            resources=[
                "Data Engineering Cookbook",
            ],
            unlocks=["feature pipelines", "real-time ml"],
            ats_gain=3,
        ),
    },
)
ROLE_SKILL_MAPS["ai engineer"] = _ai_engineer


# ──────────────────────────────────────────────
# Backend Engineer
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["backend engineer"] = RoleSkillMap(
    title="Backend Engineer",
    aliases=[
        "backend engineer",
        "backend developer",
        "back end engineer",
        "back end developer",
    ],
    description="Designs and builds server-side logic, APIs, databases, and infrastructure that power web and mobile applications.",
    estimated_months=10,
    skills={
        "python": SkillInfo(
            name="python", tier="core", priority=5,
            reason="Primary language for backend frameworks like Flask, Django, and FastAPI", learning_time_weeks=6,
            resources=["Python.org official tutorial"],
            unlocks=["flask", "django", "fastapi"], ats_gain=8,
        ),
        "sql": SkillInfo(
            name="sql", tier="core", priority=5,
            reason="Data persistence and querying are the foundation of backend development", learning_time_weeks=4,
            resources=["SQLZoo"],
            unlocks=["postgresql", "database design"], ats_gain=7,
        ),
        "rest apis": SkillInfo(
            name="rest apis", tier="core", priority=5,
            reason="Backend services communicate via APIs; designing RESTful endpoints is the core deliverable", learning_time_weeks=3,
            resources=["REST API Tutorial"],
            unlocks=["graphql", "microservices"], ats_gain=7,
        ),
        "git": SkillInfo(
            name="git", tier="core", priority=5,
            reason="Version control is mandatory for any software engineering role", learning_time_weeks=2,
            resources=["Pro Git"],
            unlocks=["ci/cd", "collaboration"], ats_gain=5,
        ),
        "postgresql": SkillInfo(
            name="postgresql", tier="core", priority=4,
            reason="The most widely used production database for backend applications", learning_time_weeks=4,
            resources=["PostgreSQL Tutorial"],
            unlocks=["database optimization"], ats_gain=6,
        ),
        "docker": SkillInfo(
            name="docker", tier="core", priority=4,
            reason="Containerization is the standard for backend deployment and development environments", learning_time_weeks=3,
            resources=["Docker Get Started"],
            unlocks=["ci/cd", "orchestration"], ats_gain=6,
        ),
        "testing": SkillInfo(
            name="testing", tier="intermediate", priority=4,
            reason="Backend reliability depends on thorough unit and integration testing", learning_time_weeks=3,
            resources=["Pytest docs"],
            unlocks=["tdd", "ci/cd"], ats_gain=5,
        ),
        "linux": SkillInfo(
            name="linux", tier="intermediate", priority=4,
            reason="Most servers run Linux; command-line, process management, and basic sysadmin are required", learning_time_weeks=3,
            resources=["Linux Journey"],
            unlocks=["devops", "server management"], ats_gain=5,
        ),
        "ci/cd": SkillInfo(
            name="ci/cd", tier="intermediate", priority=3,
            reason="Automated testing and deployment pipelines are standard in modern backend teams", learning_time_weeks=3,
            resources=["GitHub Actions docs"],
            unlocks=["devops", "automation"], ats_gain=4,
        ),
        "redis": SkillInfo(
            name="redis", tier="advanced", priority=2,
            reason="Caching, rate limiting, and job queues improve application performance and scalability", learning_time_weeks=2,
            resources=["Redis University"],
            unlocks=["caching", "message queues"], ats_gain=3,
        ),
        "cloud": SkillInfo(
            name="cloud", tier="advanced", priority=2,
            reason="Cloud platforms provide compute, storage, and networking for backend services", learning_time_weeks=5,
            resources=["AWS Cloud Practitioner"],
            unlocks=["serverless", "scalable infrastructure"], ats_gain=4,
        ),
        "system design": SkillInfo(
            name="system design", tier="advanced", priority=2,
            reason="Architecture decisions impact scalability, reliability, and maintainability", learning_time_weeks=8,
            resources=["System Design Interview"],
            unlocks=["senior roles", "architecture"], ats_gain=3,
        ),
    },
)


# ──────────────────────────────────────────────
# Frontend Engineer
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["frontend engineer"] = RoleSkillMap(
    title="Frontend Engineer",
    aliases=[
        "frontend engineer",
        "frontend developer",
        "front end engineer",
        "front end developer",
        "ui engineer",
        "ui developer",
    ],
    description="Builds responsive, accessible, and performant user interfaces for web applications, focusing on user experience and visual design.",
    estimated_months=10,
    skills={
        "html": SkillInfo(
            name="html", tier="core", priority=5,
            reason="The structural foundation of every web page", learning_time_weeks=2,
            resources=["MDN HTML docs"],
            unlocks=["css", "accessibility"], ats_gain=4,
        ),
        "css": SkillInfo(
            name="css", tier="core", priority=5,
            reason="Controls visual presentation, layout, and responsiveness", learning_time_weeks=4,
            resources=["MDN CSS docs"],
            unlocks=["tailwind", "responsive design"], ats_gain=4,
        ),
        "javascript": SkillInfo(
            name="javascript", tier="core", priority=5,
            reason="The programming language of the browser; required for all interactive web development", learning_time_weeks=6,
            resources=["MDN JavaScript Guide"],
            unlocks=["react", "typescript"], ats_gain=9,
        ),
        "react": SkillInfo(
            name="react", tier="core", priority=5,
            reason="The dominant frontend framework; used by most modern web applications", learning_time_weeks=8,
            resources=["React.dev tutorial"],
            unlocks=["next.js", "react native"], ats_gain=9,
        ),
        "typescript": SkillInfo(
            name="typescript", tier="core", priority=5,
            reason="Type safety catches bugs at compile time and improves code maintainability at scale", learning_time_weeks=4,
            resources=["TypeScript Handbook"],
            unlocks=["type-safe apps", "large codebases"], ats_gain=7,
        ),
        "git": SkillInfo(
            name="git", tier="core", priority=4,
            reason="Version control for collaborative frontend development", learning_time_weeks=2,
            resources=["Pro Git"],
            unlocks=["ci/cd", "team collaboration"], ats_gain=4,
        ),
        "rest apis": SkillInfo(
            name="rest apis", tier="intermediate", priority=4,
            reason="Frontend apps consume APIs for data; understanding HTTP, fetch, and integration patterns is essential", learning_time_weeks=2,
            resources=["REST API Tutorial"],
            unlocks=["full-stack integration"], ats_gain=5,
        ),
        "testing": SkillInfo(
            name="testing", tier="intermediate", priority=4,
            reason="Component, integration, and e2e testing catch UI regressions and ensure reliability", learning_time_weeks=4,
            resources=["Testing Library docs", "Cypress docs"],
            unlocks=["jest", "cypress"], ats_gain=5,
        ),
        "tailwind css": SkillInfo(
            name="tailwind css", tier="intermediate", priority=4,
            reason="Utility-first framework that accelerates UI development with consistent design tokens", learning_time_weeks=2,
            resources=["Tailwind CSS docs"],
            unlocks=["rapid prototyping"], ats_gain=4,
        ),
        "next.js": SkillInfo(
            name="next.js", tier="intermediate", priority=4,
            reason="The leading React framework providing SSR, SSG, routing, and optimizing performance", learning_time_weeks=4,
            resources=["Next.js docs"],
            unlocks=["ssr", "seo", "full-stack"], ats_gain=7,
        ),
        "accessibility": SkillInfo(
            name="accessibility", tier="advanced", priority=3,
            reason="WCAG compliance is increasingly required and improves UX for all users", learning_time_weeks=3,
            resources=["WebAIM", "MDN Accessibility"],
            unlocks=["inclusive design", "compliance"], ats_gain=3,
        ),
    },
)


# ──────────────────────────────────────────────
# Data Engineer
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["data engineer"] = RoleSkillMap(
    title="Data Engineer",
    aliases=[
        "data engineer",
        "data engineer",
        "data pipeline engineer",
        "big data engineer",
    ],
    description="Designs, builds, and maintains data pipelines, warehouses, and ETL processes that make data accessible and reliable for analytics and machine learning.",
    estimated_months=12,
    skills={
        "python": SkillInfo(
            name="python", tier="core", priority=5,
            reason="Primary language for ETL scripts, data processing, and pipeline orchestration", learning_time_weeks=4,
            resources=["Python.org tutorial"],
            unlocks=["pandas", "airflow", "spark"], ats_gain=7,
        ),
        "sql": SkillInfo(
            name="sql", tier="core", priority=5,
            reason="The universal language for data extraction, transformation, and querying in warehouses", learning_time_weeks=4,
            resources=["SQLZoo"],
            unlocks=["postgresql", "data warehousing"], ats_gain=8,
        ),
        "etl": SkillInfo(
            name="etl", tier="core", priority=5,
            reason="Extract, transform, load is the core workflow of data engineering", learning_time_weeks=4,
            resources=["Data Engineering Cookbook"],
            unlocks=["data pipelines", "warehousing"], ats_gain=7,
        ),
        "git": SkillInfo(
            name="git", tier="core", priority=4,
            reason="Version control for pipeline code and configuration", learning_time_weeks=2,
            resources=["Pro Git"],
            unlocks=["ci/cd", "collaboration"], ats_gain=4,
        ),
        "docker": SkillInfo(
            name="docker", tier="core", priority=4,
            reason="Containerization ensures reproducible data pipeline environments", learning_time_weeks=2,
            resources=["Docker Get Started"],
            unlocks=["pipeline deployment", "spark clusters"], ats_gain=5,
        ),
        "cloud": SkillInfo(
            name="cloud", tier="core", priority=4,
            reason="Cloud data platforms (AWS/GCP/Azure) provide scalable storage and compute for data workloads", learning_time_weeks=5,
            resources=["AWS Cloud Practitioner"],
            unlocks=["data lake", "warehouse"], ats_gain=6,
        ),
        "spark": SkillInfo(
            name="spark", tier="intermediate", priority=4,
            reason="Distributed computing framework for large-scale data processing", learning_time_weeks=6,
            resources=["Spark official docs"],
            unlocks=["big data", "streaming"], ats_gain=6,
        ),
        "airflow": SkillInfo(
            name="airflow", tier="intermediate", priority=4,
            reason="The most popular workflow orchestration tool for scheduling and monitoring data pipelines", learning_time_weeks=4,
            resources=["Airflow docs"],
            unlocks=["pipeline orchestration", "monitoring"], ats_gain=6,
        ),
        "data modeling": SkillInfo(
            name="data modeling", tier="intermediate", priority=4,
            reason="Star schemas, dimension modeling, and normalization are essential for warehouse design", learning_time_weeks=4,
            resources=["Kimball Data Warehouse Toolkit"],
            unlocks=["warehouse design", "analytics"], ats_gain=5,
        ),
        "postgresql": SkillInfo(
            name="postgresql", tier="intermediate", priority=3,
            reason="Relational database for storing processed data and metadata", learning_time_weeks=3,
            resources=["PostgreSQL Tutorial"],
            unlocks=["data storage", "query optimization"], ats_gain=4,
        ),
    },
)


# ──────────────────────────────────────────────
# DevOps Engineer
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["devops engineer"] = RoleSkillMap(
    title="DevOps Engineer",
    aliases=[
        "devops engineer",
        "devops engineer",
        "platform engineer",
        "site reliability engineer",
        "sre",
    ],
    description="Builds and maintains CI/CD pipelines, infrastructure automation, monitoring, and deployment systems that enable reliable software delivery at scale.",
    estimated_months=12,
    skills={
        "linux": SkillInfo(
            name="linux", tier="core", priority=5,
            reason="Servers and containers run on Linux; sysadmin skills are the foundation of DevOps", learning_time_weeks=4,
            resources=["Linux Journey"],
            unlocks=["bash scripting", "server management"], ats_gain=7,
        ),
        "docker": SkillInfo(
            name="docker", tier="core", priority=5,
            reason="Containerization is the building block of modern deployment pipelines", learning_time_weeks=3,
            resources=["Docker Get Started"],
            unlocks=["kubernetes", "ci/cd"], ats_gain=7,
        ),
        "kubernetes": SkillInfo(
            name="kubernetes", tier="core", priority=5,
            reason="The standard container orchestration platform; required for managing production services at scale", learning_time_weeks=8,
            resources=["Kubernetes official docs"],
            unlocks=["helm", "service mesh", "scalability"], ats_gain=8,
        ),
        "ci/cd": SkillInfo(
            name="ci/cd", tier="core", priority=5,
            reason="Automation of build, test, and deploy pipelines is the core DevOps deliverable", learning_time_weeks=4,
            resources=["GitHub Actions docs", "GitLab CI docs"],
            unlocks=["automated deployment", "gitops"], ats_gain=7,
        ),
        "git": SkillInfo(
            name="git", tier="core", priority=4,
            reason="Version control for infrastructure as code and pipeline definitions", learning_time_weeks=2,
            resources=["Pro Git"],
            unlocks=["ci/cd", "collaboration"], ats_gain=4,
        ),
        "cloud": SkillInfo(
            name="cloud", tier="core", priority=4,
            reason="Cloud platforms provide infrastructure primitives for compute, networking, and storage", learning_time_weeks=5,
            resources=["AWS Cloud Practitioner"],
            unlocks=["iaas", "scalability"], ats_gain=6,
        ),
        "terraform": SkillInfo(
            name="terraform", tier="intermediate", priority=4,
            reason="The leading IaC tool for provisioning and managing cloud infrastructure declaratively", learning_time_weeks=4,
            resources=["Terraform official tutorials"],
            unlocks=["infrastructure as code", "multi-cloud"], ats_gain=7,
        ),
        "monitoring": SkillInfo(
            name="monitoring", tier="intermediate", priority=4,
            reason="Observability (metrics, logs, traces) is required to ensure system reliability and debug issues", learning_time_weeks=4,
            resources=["Prometheus docs", "Grafana tutorials"],
            unlocks=["alerting", "slo/sli"], ats_gain=5,
        ),
        "python": SkillInfo(
            name="python", tier="intermediate", priority=3,
            reason="Scripting automation, tooling, and custom operators in DevOps workflows", learning_time_weeks=3,
            resources=["Python.org tutorial"],
            unlocks=["automation scripts", "tooling"], ats_gain=4,
        ),
        "networking": SkillInfo(
            name="networking", tier="advanced", priority=3,
            reason="Understanding DNS, load balancing, firewalls, and VPCs is essential for infrastructure design", learning_time_weeks=4,
            resources=["Professor Messer Network+"],
            unlocks=["network security", "architecture"], ats_gain=4,
        ),
    },
)


# ──────────────────────────────────────────────
# Cloud Engineer
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["cloud engineer"] = RoleSkillMap(
    title="Cloud Engineer",
    aliases=[
        "cloud engineer",
        "cloud engineer",
        "cloud architect",
        "cloud infrastructure engineer",
    ],
    description="Designs, implements, and manages cloud infrastructure across AWS, Azure, or GCP, ensuring scalability, security, and cost efficiency.",
    estimated_months=10,
    skills={
        "cloud": SkillInfo(
            name="cloud", tier="core", priority=5,
            reason="Foundational understanding of cloud computing, regions, availability zones, and shared responsibility model", learning_time_weeks=3,
            resources=["AWS Cloud Practitioner"],
            unlocks=["aws", "gcp", "azure"], ats_gain=7,
        ),
        "aws": SkillInfo(
            name="aws", tier="core", priority=5,
            reason="AWS is the leading cloud provider; core services (EC2, S3, VPC, IAM) are fundamental", learning_time_weeks=8,
            resources=["AWS docs", "A Cloud Guru"],
            unlocks=["serverless", "infrastructure design"], ats_gain=9,
        ),
        "docker": SkillInfo(
            name="docker", tier="core", priority=4,
            reason="Containers are the standard compute unit in cloud environments", learning_time_weeks=2,
            resources=["Docker Get Started"],
            unlocks=["ecs", "eks", "fargate"], ats_gain=5,
        ),
        "linux": SkillInfo(
            name="linux", tier="core", priority=4,
            reason="Cloud servers overwhelmingly run Linux; administration is required", learning_time_weeks=3,
            resources=["Linux Journey"],
            unlocks=["server management", "automation"], ats_gain=5,
        ),
        "ci/cd": SkillInfo(
            name="ci/cd", tier="core", priority=4,
            reason="Cloud infrastructure is managed through automated pipelines", learning_time_weeks=3,
            resources=["GitHub Actions docs"],
            unlocks=["deployment automation"], ats_gain=5,
        ),
        "terraform": SkillInfo(
            name="terraform", tier="intermediate", priority=4,
            reason="IaC for provisioning and managing cloud resources declaratively", learning_time_weeks=4,
            resources=["Terraform tutorials"],
            unlocks=["infrastructure as code"], ats_gain=6,
        ),
        "kubernetes": SkillInfo(
            name="kubernetes", tier="intermediate", priority=4,
            reason="Container orchestration for running production workloads in the cloud", learning_time_weeks=6,
            resources=["Kubernetes docs"],
            unlocks=["eks", "gke", "aks"], ats_gain=6,
        ),
        "networking": SkillInfo(
            name="networking", tier="intermediate", priority=4,
            reason="VPC design, subnets, routing, VPN, and CDN are core cloud infrastructure tasks", learning_time_weeks=4,
            resources=["AWS VPC docs"],
            unlocks=["network architecture", "security"], ats_gain=5,
        ),
        "python": SkillInfo(
            name="python", tier="advanced", priority=3,
            reason="Scripting automation and custom infrastructure tooling", learning_time_weeks=3,
            resources=["Python.org tutorial"],
            unlocks=["automation", "cdk"], ats_gain=3,
        ),
    },
)


# ──────────────────────────────────────────────
# Product Manager
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["product manager"] = RoleSkillMap(
    title="Product Manager",
    aliases=[
        "product manager",
        "product manager",
        "pm",
        "technical product manager",
    ],
    description="Defines product vision, strategy, and roadmap by understanding user needs, market opportunities, and business goals to guide cross-functional teams.",
    estimated_months=6,
    skills={
        "analytics": SkillInfo(
            name="analytics", tier="core", priority=5,
            reason="Data-driven decision making is the foundation of product management; requires proficiency in metrics, A/B testing, and tools", learning_time_weeks=4,
            resources=["Coursera Product Analytics"],
            unlocks=["a/b testing", "metrics-driven decisions"], ats_gain=7,
        ),
        "product strategy": SkillInfo(
            name="product strategy", tier="core", priority=5,
            reason="Vision setting, market analysis, competitive research, and strategic roadmapping define the PM role", learning_time_weeks=6,
            resources=["Inspired (Marty Cagan)"],
            unlocks=["roadmapping", "stakeholder alignment"], ats_gain=8,
        ),
        "agile": SkillInfo(
            name="agile", tier="core", priority=5,
            reason="Scrum and Kanban are the standard frameworks for software product development", learning_time_weeks=3,
            resources=["Scrum Guide"],
            unlocks=["sprint planning", "retrospectives"], ats_gain=6,
        ),
        "user research": SkillInfo(
            name="user research", tier="core", priority=5,
            reason="Understanding user needs through interviews, surveys, and usability testing ensures products solve real problems", learning_time_weeks=4,
            resources=["Nielsen Norman Group"],
            unlocks=["ux design", "jobs-to-be-done"], ats_gain=6,
        ),
        "a/b testing": SkillInfo(
            name="a/b testing", tier="intermediate", priority=4,
            reason="Scientific experimentation drives feature decisions and optimization", learning_time_weeks=3,
            resources=["Optimizely A/B Testing guide"],
            unlocks=["experimentation", "optimization"], ats_gain=5,
        ),
        "wireframing": SkillInfo(
            name="wireframing", tier="intermediate", priority=4,
            reason="Communicating product ideas through sketches, wireframes, and prototypes before development", learning_time_weeks=3,
            resources=["Figma tutorials"],
            unlocks=["prototyping", "specs"], ats_gain=5,
        ),
        "technical": SkillInfo(
            name="technical", tier="intermediate", priority=3,
            reason="Understanding technical concepts and constraints enables effective communication with engineering teams", learning_time_weeks=4,
            resources=["The Tech PM Handbook"],
            unlocks=["engineering collaboration", "technical decisions"], ats_gain=4,
        ),
    },
)


# ──────────────────────────────────────────────
# Data Scientist
# ──────────────────────────────────────────────
ROLE_SKILL_MAPS["data scientist"] = RoleSkillMap(
    title="Data Scientist",
    aliases=[
        "data scientist",
        "data scientist",
        "data science",
        "data analyst",
    ],
    description="Analyzes complex data sets, builds statistical models, and generates actionable insights to drive business decisions.",
    estimated_months=12,
    skills={
        "python": SkillInfo(
            name="python", tier="core", priority=5,
            reason="Primary language for data analysis, modeling, and visualization", learning_time_weeks=4,
            resources=["Python.org tutorial"],
            unlocks=["pandas", "scikit-learn", "visualization"], ats_gain=8,
        ),
        "sql": SkillInfo(
            name="sql", tier="core", priority=5,
            reason="Extracting and manipulating data from databases is a daily task", learning_time_weeks=3,
            resources=["SQLZoo"],
            unlocks=["data extraction", "analytics"], ats_gain=7,
        ),
        "statistics": SkillInfo(
            name="statistics", tier="core", priority=5,
            reason="Hypothesis testing, distributions, regression, and probability are fundamental to data science", learning_time_weeks=8,
            resources=["Statistics 101 (Khan Academy)"],
            unlocks=["experiments", "predictive models"], ats_gain=7,
        ),
        "machine learning": SkillInfo(
            name="machine learning", tier="core", priority=5,
            reason="Classification, regression, clustering, and model evaluation are core data science methodologies", learning_time_weeks=8,
            resources=["Andrew Ng ML course"],
            unlocks=["deep learning", "nlp"], ats_gain=8,
        ),
        "data visualization": SkillInfo(
            name="data visualization", tier="core", priority=4,
            reason="Communicating insights through compelling visualizations is a key deliverable", learning_time_weeks=3,
            resources=["Storytelling with Data (Cole Knaflic)"],
            unlocks=["tableau", "matplotlib", "dashboards"], ats_gain=5,
        ),
        "pandas": SkillInfo(
            name="pandas", tier="core", priority=5,
            reason="Essential tool for data manipulation, cleaning, and exploration in Python", learning_time_weeks=3,
            resources=["Pandas documentation"],
            unlocks=["data analysis", "feature engineering"], ats_gain=6,
        ),
        "git": SkillInfo(
            name="git", tier="core", priority=3,
            reason="Version control for notebooks, code, and analysis scripts", learning_time_weeks=2,
            resources=["Pro Git"],
            unlocks=["collaboration", "reproducibility"], ats_gain=3,
        ),
        "a/b testing": SkillInfo(
            name="a/b testing", tier="intermediate", priority=4,
            reason="Designing and analyzing experiments is a key data science skill for product teams", learning_time_weeks=3,
            resources=["Trustworthy Online Controlled Experiments (Kohavi)"],
            unlocks=["experiment design", "causal inference"], ats_gain=5,
        ),
        "deep learning": SkillInfo(
            name="deep learning", tier="advanced", priority=3,
            reason="Neural network understanding for advanced modeling tasks like NLP and computer vision", learning_time_weeks=8,
            resources=["Fast.ai"],
            unlocks=["nlp", "computer vision"], ats_gain=4,
        ),
    },
)


def get_role_skill_map(target_role: str | None) -> RoleSkillMap | None:
    """Find the best-matching RoleSkillMap for a target role string."""
    if not target_role:
        return None
    key = target_role.lower().strip()

    for map_key, rsm in ROLE_SKILL_MAPS.items():
        if key == map_key:
            return rsm
        if key in rsm.aliases:
            return rsm

    # Fuzzy match: check if user's role string contains a known alias
    for rsm in ROLE_SKILL_MAPS.values():
        for alias in rsm.aliases:
            if alias in key or key in alias:
                return rsm

    return None
