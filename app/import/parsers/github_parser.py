import requests
from collections import Counter
from .base import BaseParser


GITHUB_API = "https://api.github.com"


class GitHubParser(BaseParser):
    def __init__(self, token=None):
        self.token = token

    def _headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, url):
        resp = requests.get(url, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def parse(self, raw_data) -> dict:
        username = raw_data.strip() if isinstance(raw_data, str) else str(raw_data)
        result = self._empty_result()

        try:
            user = self._get(f"{GITHUB_API}/users/{username}")
        except requests.RequestException:
            return result

        pi = result["personal_info"]
        pi["full_name"] = user.get("name") or username
        pi["location"] = user.get("location") or ""
        pi["github"] = user.get("html_url", f"https://github.com/{username}")
        pi["website"] = user.get("blog") or ""
        result["summary"] = user.get("bio") or ""

        try:
            repos = self._get(
                f"{GITHUB_API}/users/{username}/repos?per_page=100&sort=updated"
            )
        except requests.RequestException:
            repos = []

        lang_counter = Counter()
        for repo in repos:
            if repo.get("fork"):
                continue
            proj = {
                "name": repo.get("name", ""),
                "description": repo.get("description") or "",
                "url": repo.get("html_url", ""),
                "technologies": [],
            }
            if repo.get("language"):
                lang_counter[repo["language"]] += 1
                proj["technologies"] = [repo["language"]]

            try:
                lang_data = self._get(repo["languages_url"])
                proj["technologies"] = (
                    list(lang_data.keys()) if lang_data else proj["technologies"]
                )
                for lang in lang_data:
                    lang_counter[lang] += 1
            except requests.RequestException:
                pass

            result["projects"].append(proj)

        result["skills"] = [lang for lang, _ in lang_counter.most_common(20)]

        return result
