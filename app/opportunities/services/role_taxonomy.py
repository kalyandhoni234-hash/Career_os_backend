"""
Maps a user's target/dream role to a broader set of related role keywords,
so recommendations surface adjacent roles in the same domain — not just
opportunities whose title is an exact substring match.

e.g. target_role="Cybersecurity" should also surface "SOC Analyst",
"Penetration Tester", "Security Engineer", "GRC Analyst", etc.
"""

ROLE_DOMAINS: dict[str, list[str]] = {
    "cybersecurity": [
        "cybersecurity", "cyber security", "security analyst", "security engineer",
        "soc analyst", "soc engineer", "security operations",
        "penetration tester", "pentester", "pentest", "ethical hacker",
        "red team", "blue team", "purple team",
        "incident response", "threat intelligence", "threat hunter",
        "vulnerability", "grc analyst", "compliance analyst",
        "application security", "appsec", "cloud security",
        "network security", "information security", "infosec",
        "malware analyst", "security consultant", "ciso",
        "iam analyst", "identity and access", "devsecops",
    ],
    "data": [
        "data analyst", "data scientist", "data engineer", "analytics engineer",
        "business intelligence", "bi developer", "machine learning engineer",
        "ml engineer", "ai engineer", "data science",
    ],
    "software": [
        "software engineer", "software developer", "backend engineer",
        "frontend engineer", "full stack", "fullstack", "sde",
        "application developer", "systems engineer",
    ],
    "cloud_devops": [
        "devops engineer", "cloud engineer", "site reliability", "sre",
        "platform engineer", "infrastructure engineer", "cloud architect",
    ],
    "networking": [
        "network engineer", "network administrator", "systems administrator",
        "network architect", "noc engineer",
    ],
}


def expand_role_keywords(target_role: str) -> list[str]:
    """
    Given a free-text dream/target role, return a list of related
    keywords to search across job titles and tech stacks.

    Falls back to the individual words of target_role if no known
    domain matches, so the feature still works for roles outside
    the curated taxonomy.
    """
    if not target_role:
        return []

    role_lower = target_role.strip().lower()
    keywords: set[str] = {role_lower}

    for domain_terms in ROLE_DOMAINS.values():
        if any(term in role_lower for term in domain_terms):
            keywords.update(domain_terms)
            break

    if len(keywords) == 1:
        words = [w for w in role_lower.split() if len(w) > 2]
        keywords.update(words)

    return list(keywords)