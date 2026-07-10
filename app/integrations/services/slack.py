import logging
import requests
from flask import current_app
from . import BaseIntegrationService

logger = logging.getLogger(__name__)


class SlackService(BaseIntegrationService):
    provider = "slack"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("SLACK_CLIENT_ID") and cfg.get("SLACK_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        cfg = current_app.config
        client_id = cfg["SLACK_CLIENT_ID"]
        scope = "chat:write,channels:read,users:read"
        url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}&scope={scope}&redirect_uri={redirect_uri}"
        )
        if state:
            url += f"&state={state}"
        return url

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": cfg["SLACK_CLIENT_ID"],
                "client_secret": cfg["SLACK_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack OAuth error: {data.get('error', 'unknown')}")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "scope": data.get("scope", ""),
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": cfg["SLACK_CLIENT_ID"],
                "client_secret": cfg["SLACK_CLIENT_SECRET"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"Slack token refresh error: {data.get('error', 'unknown')}"
            )
        return data

    def sync_data(self, access_token: str) -> dict:
        team_info = {}
        try:
            auth_resp = requests.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if auth_resp.ok:
                auth_data = auth_resp.json()
                if auth_data.get("ok"):
                    team_info = {
                        "team": auth_data.get("team", ""),
                        "team_id": auth_data.get("team_id", ""),
                        "user_id": auth_data.get("user_id", ""),
                        "url": auth_data.get("url", ""),
                    }
        except Exception as e:
            logger.warning("Slack auth test failed: %s", e)

        return {
            "provider_user_id": team_info.get("user_id", ""),
            "provider_username": team_info.get("team", ""),
            "provider_data": {
                "team": team_info.get("team", ""),
                "team_id": team_info.get("team_id", ""),
                "workspace_url": team_info.get("url", ""),
                "channels": [],
                "notifications_enabled": True,
            },
        }
