import logging
import requests
from flask import current_app
from . import BaseIntegrationService

logger = logging.getLogger(__name__)

AUTHORITY = "https://login.microsoftonline.com/common"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookService(BaseIntegrationService):
    provider = "outlook"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("OUTLOOK_CLIENT_ID") and cfg.get("OUTLOOK_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        cfg = current_app.config
        client_id = cfg["OUTLOOK_CLIENT_ID"]
        scope = "Calendars.Read Mail.Read offline_access"
        url = (
            f"{AUTHORITY}/oauth2/v2.0/authorize"
            f"?client_id={client_id}&response_type=code"
            f"&redirect_uri={redirect_uri}&scope={scope}"
        )
        if state:
            url += f"&state={state}"
        return url

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data={
                "client_id": cfg["OUTLOOK_CLIENT_ID"],
                "client_secret": cfg["OUTLOOK_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(
                f"Outlook OAuth error: {data.get('error_description', data['error'])}"
            )
        return data

    def refresh_access_token(self, refresh_token: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data={
                "client_id": cfg["OUTLOOK_CLIENT_ID"],
                "client_secret": cfg["OUTLOOK_CLIENT_SECRET"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _graph_get(self, token: str, path: str):
        resp = requests.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def sync_data(self, access_token: str) -> dict:
        events = []
        try:
            cal_data = self._graph_get(
                access_token, "/me/calendar/events?$top=50&$orderBy=start/dateTime"
            )
            for item in cal_data.get("value", []):
                events.append(
                    {
                        "id": item.get("id"),
                        "subject": item.get("subject", ""),
                        "start": item.get("start", {}).get("dateTime", ""),
                        "end": item.get("end", {}).get("dateTime", ""),
                        "location": item.get("location", {}).get("displayName", ""),
                        "is_online": item.get("isOnlineMeeting", False),
                        "online_link": item.get("onlineMeetingUrl", ""),
                    }
                )

            interview_events = [
                e for e in events if "interview" in e.get("subject", "").lower()
            ]
        except Exception as e:
            logger.warning("Outlook calendar sync failed: %s", e)
            interview_events = []

        emails = []
        try:
            mail_data = self._graph_get(
                access_token,
                "/me/messages?$top=20&$orderBy=receivedDateTime desc&$select=subject,receivedDateTime,from,isRead",
            )
            for item in mail_data.get("value", []):
                emails.append(
                    {
                        "id": item.get("id"),
                        "subject": item.get("subject", ""),
                        "received": item.get("receivedDateTime", ""),
                        "from": item.get("from", {})
                        .get("emailAddress", {})
                        .get("address", ""),
                        "is_read": item.get("isRead", False),
                    }
                )

            interview_mails = [
                e
                for e in emails
                if "interview" in e.get("subject", "").lower()
                or "application" in e.get("subject", "").lower()
                or "job" in e.get("subject", "").lower()
            ]
        except Exception as e:
            logger.warning("Outlook mail sync failed: %s", e)
            interview_mails = []
            emails = []

        return {
            "provider_data": {
                "total_calendar_events": len(events),
                "interview_events": len(interview_events),
                "calendar_events": events[:20],
                "total_emails": len(emails),
                "career_emails": len(interview_mails),
                "recent_emails": emails[:10],
            },
        }
