import logging
import requests
from flask import current_app
from . import BaseIntegrationService

logger = logging.getLogger(__name__)


class GoogleDriveService(BaseIntegrationService):
    provider = "google_drive"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("GOOGLE_CLIENT_ID") and cfg.get("GOOGLE_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        cfg = current_app.config
        client_id = cfg["GOOGLE_CLIENT_ID"]
        scope = "https://www.googleapis.com/auth/drive.readonly"
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
        files = []
        try:
            mime_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.google-apps.document",
                "application/vnd.google-apps.presentation",
                "application/vnd.google-apps.folder",
            ]
            query = " or ".join(f"mimeType='{m}'" for m in mime_types)
            resp = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                params={
                    "q": f"({query}) and trashed=false",
                    "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink,iconLink)",
                    "orderBy": "modifiedTime desc",
                    "pageSize": 50,
                },
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                for f in data.get("files", []):
                    files.append(
                        {
                            "id": f.get("id"),
                            "name": f.get("name"),
                            "mime_type": f.get("mimeType"),
                            "modified_time": f.get("modifiedTime"),
                            "size": f.get("size"),
                            "web_link": f.get("webViewLink"),
                        }
                    )

            resumes = [
                f
                for f in files
                if any(kw in f["name"].lower() for kw in ["resume", "cv", "curriculum"])
            ]
            certificates = [
                f
                for f in files
                if any(
                    kw in f["name"].lower()
                    for kw in ["certificate", "certification", "credential"]
                )
            ]

        except Exception as e:
            logger.warning("Google Drive sync failed: %s", e)

        return {
            "provider_data": {
                "total_files": len(files),
                "resume_files": len(resumes),
                "certificate_files": len(certificates),
                "recent_files": files[:10],
                "resumes": resumes[:5],
                "certificates": certificates[:5],
            },
        }
