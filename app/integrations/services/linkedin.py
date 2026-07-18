import logging
import requests
from flask import current_app
from . import BaseIntegrationService

logger = logging.getLogger(__name__)


class LinkedInService(BaseIntegrationService):
    provider = "linkedin"

    def is_configured(self) -> bool:
        cfg = current_app.config
        return bool(cfg.get("LINKEDIN_CLIENT_ID") and cfg.get("LINKEDIN_CLIENT_SECRET"))

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        import urllib.parse

        cfg = current_app.config
        client_id = cfg["LINKEDIN_CLIENT_ID"]
        scope = "openid,profile,email"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
        }
        if state:
            params["state"] = state
        return (
            "https://www.linkedin.com/oauth/v2/authorization?"
            + urllib.parse.urlencode(params)
        )

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        cfg = current_app.config
        resp = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cfg["LINKEDIN_CLIENT_ID"],
                "client_secret": cfg["LINKEDIN_CLIENT_SECRET"],
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(
                f"LinkedIn OAuth error: {data.get('error_description', data['error'])}"
            )
        return data

    def refresh_access_token(self, refresh_token: str) -> dict:
        raise RuntimeError(
            "LinkedIn OAuth 2.0 does not support refresh tokens for all apps; reconnect required"
        )

    def _li_get(self, token: str, path: str):
        resp = requests.get(
            f"https://api.linkedin.com/v2{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def sync_data(self, access_token: str) -> dict:
        # ── Stage 1: /userinfo ──────────────────────────────────
        logger.info("LINKEDIN SYNC: fetching /userinfo")
        user_info = self._li_get(access_token, "/userinfo")
        sub = user_info.get("sub", "")
        name = user_info.get("name", "")
        email = user_info.get("email", "")
        given_name = user_info.get("given_name", "")
        family_name = user_info.get("family_name", "")
        picture = user_info.get("picture", "")

        logger.debug(
            "LINKEDIN SYNC /userinfo: sub=%s email=%s email_verified=%s",
            sub, email, user_info.get("email_verified"),
        )

        profile_email = bool(user_info.get("email_verified")) if email else None

        provider_data = {
            "name": name,
            "given_name": given_name,
            "family_name": family_name,
            "picture": picture,
            "email_verified": profile_email,
        }

        # ── Stage 2: /me (basic profile) ────────────────────────
        try:
            profile_resp = requests.get(
                "https://api.linkedin.com/v2/me?projection=(id,localizedHeadline,vanityName,profilePicture)",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if profile_resp.ok:
                profile_data = profile_resp.json()
                headline = profile_data.get("localizedHeadline", "")
                vanity = profile_data.get("vanityName", "")
                provider_data["headline"] = headline
                provider_data["vanity_name"] = vanity
            else:
                logger.warning("LINKEDIN SYNC /me basic FAILED: status=%s", profile_resp.status_code)
        except Exception as e:
            logger.warning("LINKEDIN SYNC /me basic exception: %s", e)

        # ── Stage 3: /me (extended: positions, education, skills) ──
        try:
            extended_resp = requests.get(
                "https://api.linkedin.com/v2/me?projection=(id,localizedHeadline,vanityName,positions,education,skills)",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if extended_resp.ok:
                ext_data = extended_resp.json()

                positions_raw = ext_data.get("positions", {})
                if isinstance(positions_raw, dict):
                    elem = positions_raw.get("elements") or positions_raw.get("values", [])
                    if elem:
                        parsed = []
                        for p in elem:
                            entry = {
                                "title": p.get("title", ""),
                                "companyName": p.get("companyName", "")
                                or (
                                    p.get("company", {}).get("localizedName", "")
                                    if isinstance(p.get("company"), dict)
                                    else ""
                                ),
                                "start": p.get("dateRange", {}).get("start", {})
                                if isinstance(p.get("dateRange"), dict)
                                else {},
                                "end": p.get("dateRange", {}).get("end", {})
                                if isinstance(p.get("dateRange"), dict)
                                else {},
                            }
                            parsed.append(entry)
                        provider_data["experience"] = parsed

                education_raw = ext_data.get("education", {})
                if isinstance(education_raw, dict):
                    elem = education_raw.get("elements") or education_raw.get("values", [])
                    if elem:
                        parsed = []
                        for e in elem:
                            entry = {
                                "institution": e.get("institution", {}).get(
                                    "localizedName", ""
                                )
                                if isinstance(e.get("institution"), dict)
                                else e.get("institution", ""),
                                "degree": e.get("degree", ""),
                                "fieldOfStudy": e.get("fieldOfStudy", ""),
                                "start": e.get("dateRange", {}).get("start", {})
                                if isinstance(e.get("dateRange"), dict)
                                else {},
                                "end": e.get("dateRange", {}).get("end", {})
                                if isinstance(e.get("dateRange"), dict)
                                else {},
                            }
                            parsed.append(entry)
                        provider_data["education"] = parsed

                skills_raw = ext_data.get("skills", {})
                if isinstance(skills_raw, dict):
                    elem = skills_raw.get("elements") or skills_raw.get("values", [])
                    if elem:
                        parsed = []
                        for s in elem:
                            skill_name = (
                                s.get("name", {})
                                if isinstance(s.get("name"), str)
                                else (
                                    s.get("name", {}).get("localizedName", "")
                                    if isinstance(s.get("name"), dict)
                                    else ""
                                )
                            )
                            parsed.append(skill_name)
                        provider_data["skills"] = parsed
            else:
                logger.warning("LINKEDIN SYNC /me extended FAILED: status=%s", extended_resp.status_code)
        except Exception as e:
            logger.warning("LINKEDIN SYNC /me extended exception: %s", e)

        logger.debug(
            "LINKEDIN SYNC provider_data FINAL: experience=%d education=%d skills=%d",
            len(provider_data.get("experience", [])),
            len(provider_data.get("education", [])),
            len(provider_data.get("skills", [])),
        )

        result = {
            "provider_user_id": sub,
            "provider_username": family_name or given_name or name,
            "provider_email": email,
            "provider_data": provider_data,
        }
        logger.info("LINKEDIN SYNC returning: user_id=%s username=%s email=%s data_keys=%s",
                    result["provider_user_id"], result["provider_username"],
                    result["provider_email"], list(result["provider_data"].keys()))
        return result


def import_from_profile_url(url: str) -> dict:
    """
    Fallback: extract public profile info from a LinkedIn URL.
    This is a best-effort parsing - no API calls needed.
    """
    public_id = ""
    if "linkedin.com/in/" in url:
        public_id = url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
    return {
        "provider_user_id": public_id,
        "provider_username": public_id,
        "provider_data": {
            "profile_url": url,
            "public_id": public_id,
            "imported_via": "url_fallback",
        },
    }
