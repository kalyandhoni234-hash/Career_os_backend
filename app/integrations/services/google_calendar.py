import logging
import requests
from flask import current_app
from . import BaseIntegrationService, utcnow

logger = logging.getLogger(__name__)


class GoogleCalendarService(BaseIntegrationService):
    provider = "google_calendar"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("GOOGLE_CLIENT_ID") and cfg.get("GOOGLE_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        cfg = current_app.config
        client_id = cfg["GOOGLE_CLIENT_ID"]
        scope = "https://www.googleapis.com/auth/calendar.readonly"
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}&redirect_uri={redirect_uri}"
            f"&response_type=code&scope={scope}&access_type=offline&prompt=consent"
        )
        if state:
            url += f"&state={state}"
        return url

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
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
                f"Google OAuth error: {data.get('error_description', data['error'])}"
            )
        return data

    def refresh_access_token(self, refresh_token: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "refresh_token": refresh_token,
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def sync_data(self, access_token: str) -> dict:
        now = utcnow()
        events = []
        try:
            resp = requests.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                "?timeMin={}&timeMax={}&singleEvents=true&orderBy=startTime&maxResults=50".format(
                    now.isoformat(),
                    now.strftime("%Y-%m-%dT23:59:59Z"),
                ),
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                items = data.get("items", [])
                for item in items:
                    start = item.get("start", {}).get("dateTime") or item.get(
                        "start", {}
                    ).get("date", "")
                    end = item.get("end", {}).get("dateTime") or item.get(
                        "end", {}
                    ).get("date", "")
                    events.append(
                        {
                            "id": item.get("id"),
                            "summary": item.get("summary", ""),
                            "description": item.get("description", ""),
                            "start": start,
                            "end": end,
                            "location": item.get("location", ""),
                            "html_link": item.get("htmlLink", ""),
                        }
                    )
        except Exception as e:
            logger.warning("Google Calendar sync failed: %s", e)

        interview_events = [
            e
            for e in events
            if any(
                kw in (e.get("summary", "") + e.get("description", "")).lower()
                for kw in ["interview", "career", "deadline", "application"]
            )
        ]

        return {
            "provider_data": {
                "total_events": len(events),
                "interview_events": len(interview_events),
                "upcoming_events": events[:20],
            },
        }
