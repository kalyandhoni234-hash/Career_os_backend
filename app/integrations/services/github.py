import logging
import requests
from flask import current_app
from . import BaseIntegrationService

logger = logging.getLogger(__name__)


class GitHubService(BaseIntegrationService):
    provider = "github"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("GITHUB_CLIENT_ID") and cfg.get("GITHUB_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        import urllib.parse

        cfg = current_app.config
        client_id = cfg["GITHUB_CLIENT_ID"]
        scope = "read:user,user:email,repo"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
        }
        if state:
            params["state"] = state
        return (
            "https://github.com/login/oauth/authorize?"
            + urllib.parse.urlencode(params)
        )

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": cfg["GITHUB_CLIENT_ID"],
                "client_secret": cfg["GITHUB_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(
                f"GitHub OAuth error: {data.get('error_description', data['error'])}"
            )
        return data

    def refresh_access_token(self, refresh_token: str) -> dict:
        raise RuntimeError("GitHub access tokens do not expire unless revoked")

    def _gh_get(self, token: str, path: str):
        resp = requests.get(
            f"https://api.github.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CareerOS",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def sync_data(self, access_token: str) -> dict:
        user_info = self._gh_get(access_token, "/user")
        login = user_info.get("login", "")
        email = user_info.get("email", "")

        repos = self._gh_get(access_token, "/user/repos?per_page=100&sort=updated")
        repo_count = len(repos)
        languages = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        pinned = []
        try:
            pinned_query = (
                """
            query {
              user(login: \"%s\") {
                pinnedItems(first: 6, types: REPOSITORY) {
                  nodes {
                    ... on Repository {
                      name
                      description
                      url
                      primaryLanguage { name }
                      stargazerCount
                    }
                  }
                }
              }
            }
            """
                % login
            )
            pinned_resp = requests.post(
                "https://api.github.com/graphql",
                json={"query": pinned_query},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "CareerOS",
                },
                timeout=30,
            )
            if pinned_resp.ok:
                pinned_data = pinned_resp.json()
                nodes = (
                    pinned_data.get("data", {})
                    .get("user", {})
                    .get("pinnedItems", {})
                    .get("nodes", [])
                )
                pinned = [
                    {
                        "name": n.get("name"),
                        "description": n.get("description"),
                        "url": n.get("url"),
                        "language": n.get("primaryLanguage", {}).get("name")
                        if n.get("primaryLanguage")
                        else None,
                        "stars": n.get("stargazerCount", 0),
                    }
                    for n in nodes
                ]
        except Exception as e:
            logger.warning("Failed to fetch pinned repos: %s", e)

        contrib_count = 0
        try:
            contrib_query = (
                """
            query {
              user(login: \"%s\") {
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
                  }
                }
              }
            }
            """
                % login
            )
            contrib_resp = requests.post(
                "https://api.github.com/graphql",
                json={"query": contrib_query},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "CareerOS",
                },
                timeout=30,
            )
            if contrib_resp.ok:
                contrib_data = contrib_resp.json()
                contrib_count = (
                    contrib_data.get("data", {})
                    .get("user", {})
                    .get("contributionsCollection", {})
                    .get("contributionCalendar", {})
                    .get("totalContributions", 0)
                )
        except Exception as e:
            logger.warning("Failed to fetch contributions: %s", e)

        readme_links = []
        for r in repos[:5]:
            try:
                readme_resp = requests.get(
                    f"https://api.github.com/repos/{login}/{r['name']}/readme",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3.raw",
                        "User-Agent": "CareerOS",
                    },
                    timeout=10,
                )
                if readme_resp.ok:
                    readme_links.append(
                        {
                            "repo": r["name"],
                            "html_url": f"https://github.com/{login}/{r['name']}",
                        }
                    )
            except Exception as e:
                logger.warning("Failed to process repo data: %s", e)

        return {
            "provider_user_id": str(user_info.get("id", "")),
            "provider_username": login,
            "provider_email": email,
            "provider_data": {
                "name": user_info.get("name", ""),
                "repositories": repo_count,
                "contributions": contrib_count,
                "top_languages": dict(
                    sorted(languages.items(), key=lambda x: -x[1])[:8]
                ),
                "pinned_repos": pinned,
                "readme_links": readme_links,
                "bio": user_info.get("bio", ""),
                "avatar_url": user_info.get("avatar_url", ""),
                "public_repos": user_info.get("public_repos", 0),
                "followers": user_info.get("followers", 0),
                "following": user_info.get("following", 0),
                "company": user_info.get("company", ""),
                "location": user_info.get("location", ""),
                "blog": user_info.get("blog", ""),
                "twitter_username": user_info.get("twitter_username", ""),
            },
        }
