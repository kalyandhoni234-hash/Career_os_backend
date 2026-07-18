import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, redirect, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.integrations.models import Integration, OAuthState
from app.integrations.services.github import GitHubService
from app.integrations.services.linkedin import LinkedInService, import_from_profile_url
from app.integrations.services.google_calendar import GoogleCalendarService
from app.integrations.services.google_drive import GoogleDriveService
from app.integrations.services.outlook import OutlookService
from app.integrations.services.slack import SlackService
from app.integrations.profile_sync import sync_profile_from_integration

logger = logging.getLogger(__name__)

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/integrations")

PROVIDERS = {
    "github": GitHubService,
    "linkedin": LinkedInService,
    "google_calendar": GoogleCalendarService,
    "google_drive": GoogleDriveService,
    "outlook": OutlookService,
    "slack": SlackService,
}

PROVIDER_META = {
    "github": {"name": "GitHub", "icon": "github"},
    "linkedin": {"name": "LinkedIn", "icon": "linkedin"},
    "google_calendar": {"name": "Google Calendar", "icon": "google_calendar"},
    "google_drive": {"name": "Google Drive", "icon": "google_drive"},
    "outlook": {"name": "Outlook", "icon": "outlook"},
    "slack": {"name": "Slack", "icon": "slack"},
}

REDIRECT_TEMPLATE = (
    "{frontend}/settings?tab=integrations&integration={provider}&status={status}"
)


def _get_integration(user_id: int, provider: str) -> Integration:
    integration = Integration.query.filter_by(
        user_id=user_id, provider=provider
    ).first()
    if not integration:
        integration = Integration(user_id=user_id, provider=provider)
        db.session.add(integration)
        db.session.commit()
    return integration


def _get_service(provider: str) -> object:
    svc_cls = PROVIDERS.get(provider)
    if not svc_cls:
        raise ValueError(f"Unknown provider: {provider}")
    return svc_cls()


def _refresh_if_needed(integration: Integration, service: object) -> bool:
    if not integration.access_token:
        return False
    if integration.token_expiry and integration.token_expiry < datetime.now(
        timezone.utc
    ):
        if integration.refresh_token:
            try:
                token_data = service.refresh_access_token(integration.refresh_token)
                integration.access_token = token_data.get(
                    "access_token", integration.access_token
                )
                expires_in = token_data.get("expires_in")
                if expires_in:
                    integration.token_expiry = datetime.now(timezone.utc).replace(
                        tzinfo=None
                    ) + __import__("datetime").timedelta(seconds=expires_in)
                integration.refresh_token = token_data.get(
                    "refresh_token", integration.refresh_token
                )
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                logger.warning(
                    "Token refresh failed for %s: %s", integration.provider, e
                )
                integration.sync_status = "connection_error"
                integration.sync_error = str(e)
                db.session.commit()
                return False
        else:
            integration.sync_status = "connection_error"
            integration.sync_error = "Token expired and no refresh token available"
            db.session.commit()
            return False
    return True


SYNC_HISTORY_MAX = 20


def _record_sync_history(integration: Integration, status: str, summary: str = ""):
    history = integration.provider_data or {}
    sync_list = history.get("_sync_history", [])
    sync_list.append(
        {
            "synced_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "status": status,
            "summary": summary,
        }
    )
    history["_sync_history"] = sync_list[-SYNC_HISTORY_MAX:]
    integration.provider_data = history


def _check_token_health(integration: Integration) -> dict:
    if not integration.access_token:
        return {"healthy": False, "reason": "no_token", "label": "Not connected"}
    if integration.token_expiry:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if integration.token_expiry < now:
            return {
                "healthy": False,
                "reason": "expired",
                "label": "Token expired",
            }
        remaining = (integration.token_expiry - now).total_seconds()
        if remaining < 86400:
            return {
                "healthy": True,
                "warning": True,
                "reason": "expiring_soon",
                "label": "Expires soon",
                "expires_in_seconds": int(remaining),
            }
    return {"healthy": True, "reason": "ok", "label": "Active"}


# ── List all integrations ─────────────────────────────────


@integrations_bp.route("", methods=["GET"])
@login_required
def list_integrations():
    records = Integration.query.filter_by(user_id=current_user.id).all()
    connected_providers = {r.provider: r for r in records}

    result = {}
    for key, meta in PROVIDER_META.items():
        svc = _get_service(key)
        available = svc.is_configured()
        record = connected_providers.get(key)
        entry = {
            "provider": key,
            "name": meta["name"],
            "icon": meta["icon"],
            "available": available,
            "connected": record is not None
            and record.sync_status not in ("not_connected", "connection_error"),
            "sync_status": record.sync_status if record else "not_connected",
            "sync_error": record.sync_error if record else None,
            "provider_username": record.provider_username if record else None,
            "provider_email": record.provider_email if record else None,
            "connected_at": record.connected_at.isoformat()
            if record and record.connected_at
            else None,
            "last_sync_at": record.last_sync_at.isoformat()
            if record and record.last_sync_at
            else None,
            "provider_data": record.provider_data
            if record and record.provider_data
            else {},
        }
        if record and key == "linkedin":
            pd = record.provider_data or {}
            logger.debug(
                "LIST INTEGRATIONS linkedin: connected=%s experience=%d education=%d skills=%d",
                entry["connected"],
                len(pd.get("experience", [])),
                len(pd.get("education", [])),
                len(pd.get("skills", [])),
            )

        if record:
            entry["token_health"] = _check_token_health(record)
            sync_history = (record.provider_data or {}).get("_sync_history", [])
            entry["sync_history_count"] = len(sync_history)
            entry["last_sync_status"] = sync_history[-1]["status"] if sync_history else None
        else:
            entry["token_health"] = {"healthy": False, "reason": "no_token", "label": "Not connected"}
            entry["sync_history_count"] = 0
            entry["last_sync_status"] = None

        if not available:
            entry["setup_guide"] = (
                f"Configure {key.upper()}_CLIENT_ID and {key.upper()}_CLIENT_SECRET in .env"
            )
        result[key] = entry

    return jsonify({"integrations": result}), 200


# ── Connect (initiate OAuth) ───────────────────────────────


@integrations_bp.route("/<provider>/connect", methods=["POST"])
@login_required
def connect(provider):
    svc = _get_service(provider)
    if not svc.is_configured():
        return jsonify(
            {
                "error": f"{provider} is not configured",
                "setup_guide": f"Set {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET in .env",
            }
        ), 400

    state = OAuthState.create(user_id=current_user.id, provider=provider)
    redirect_uri = (
        current_app.config["BACKEND_URL"] + f"/api/integrations/{provider}/callback"
    )
    authorize_url = svc.get_authorize_url(redirect_uri, state=state)
    return jsonify({"redirect_url": authorize_url}), 200


# ── OAuth Callback ─────────────────────────────────────────


@integrations_bp.route("/<provider>/callback", methods=["GET"])
def oauth_callback(provider):
    svc = _get_service(provider)
    if not svc.is_configured():
        return jsonify({"error": f"{provider} is not configured"}), 400

    code = request.args.get("code")
    state_param = request.args.get("state", "")
    error = request.args.get("error")

    if error:
        OAuthState.cleanup_expired()
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(
            REDIRECT_TEMPLATE.format(
                frontend=frontend, provider=provider, status="error"
            )
        )

    if not code:
        return jsonify({"error": "No authorization code provided"}), 400

    if not state_param:
        logger.warning("OAuth callback missing state parameter for %s", provider)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(
            REDIRECT_TEMPLATE.format(
                frontend=frontend, provider=provider, status="error"
            )
        )

    state_data = OAuthState.consume(state_param)
    if not state_data:
        logger.warning("Invalid or expired OAuth state for %s", provider)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(
            REDIRECT_TEMPLATE.format(
                frontend=frontend, provider=provider, status="error"
            )
        )

    user_id, stored_provider = state_data
    if stored_provider != provider:
        logger.warning("State provider mismatch: %s != %s", stored_provider, provider)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(
            REDIRECT_TEMPLATE.format(
                frontend=frontend, provider=provider, status="error"
            )
        )

    redirect_uri = (
        current_app.config["BACKEND_URL"] + f"/api/integrations/{provider}/callback"
    )

    try:
        token_data = svc.exchange_code(code, redirect_uri)
    except Exception as e:
        logger.error("OAuth token exchange failed for %s: %s", provider, e)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(
            REDIRECT_TEMPLATE.format(
                frontend=frontend, provider=provider, status="error"
            )
        )

    logger.info(
        "OAUTH CALLBACK: token exchange succeeded. Keys: %s, has_access_token=%s has_refresh_token=%s",
        list(token_data.keys()),
        "access_token" in token_data,
        "refresh_token" in token_data,
    )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")

    integration = _get_integration(user_id, provider)
    integration.access_token = access_token
    integration.refresh_token = refresh_token
    if expires_in:
        integration.token_expiry = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + __import__("datetime").timedelta(seconds=expires_in)
    integration.sync_status = "connected"
    integration.sync_error = None

    try:
        sync_result = svc.sync_data(access_token)
        logger.debug(
            "OAUTH CALLBACK: sync_data returned. provider_user_id=%s",
            sync_result.get("provider_user_id"),
        )
        if sync_result.get("provider_user_id"):
            integration.provider_user_id = sync_result["provider_user_id"]
        if sync_result.get("provider_username"):
            integration.provider_username = sync_result["provider_username"]
        if sync_result.get("provider_email"):
            integration.provider_email = sync_result["provider_email"]
        if sync_result.get("provider_data"):
            existing = integration.provider_data or {}
            if isinstance(sync_result["provider_data"], dict):
                existing.update(sync_result["provider_data"])
            integration.provider_data = existing
            logger.debug(
                "OAUTH CALLBACK: merged provider_data keys=%s",
                list(integration.provider_data.keys()),
            )
        integration.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)
        integration.sync_status = "connected"
        _record_sync_history(integration, "success", "Initial sync completed")
    except Exception as e:
        logger.warning("Initial sync failed for %s: %s", provider, e)
        integration.sync_status = "sync_failed"
        integration.sync_error = str(e)
        _record_sync_history(integration, "failed", str(e))

    logger.debug(
        "OAUTH CALLBACK: before profile_sync, experience=%d education=%d skills=%d",
        len((integration.provider_data or {}).get("experience", [])),
        len((integration.provider_data or {}).get("education", [])),
        len((integration.provider_data or {}).get("skills", [])),
    )

    db.session.commit()

    try:
        sync_profile_from_integration(integration, user_id)
        from app.career.models import CareerTimelineEvent
        event = CareerTimelineEvent(
            user_id=user_id,
            event_type="integration",
            title=f"{provider.title()} Connected",
            description=f"{provider.title()} account linked and data synced",
            event_date=datetime.now(timezone.utc),
            importance=3,
        )
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("Profile sync failed after callback for %s: %s", provider, e)

    try:
        from app.core.integration import on_profile_changed
        on_profile_changed(user_id)
    except Exception as e:
        logger.warning("Integration hook failed after callback: %s", e)

    frontend = current_app.config["FRONTEND_URL"]
    return redirect(
        REDIRECT_TEMPLATE.format(frontend=frontend, provider=provider, status="success")
    )


# ── Disconnect ─────────────────────────────────────────────


@integrations_bp.route("/<provider>/disconnect", methods=["POST"])
@login_required
def disconnect(provider):
    integration = Integration.query.filter_by(
        user_id=current_user.id, provider=provider
    ).first()
    if not integration:
        return jsonify({"error": "Integration not found"}), 404

    integration.access_token = None
    integration.refresh_token = None
    integration.token_expiry = None
    integration.provider_user_id = None
    integration.provider_username = None
    integration.provider_email = None
    integration.connected_at = None
    integration.last_sync_at = None
    integration.sync_status = "not_connected"
    integration.sync_error = None
    integration.provider_data = {}
    db.session.commit()

    return jsonify({"message": f"{provider} disconnected"}), 200


# ── Sync ───────────────────────────────────────────────────


@integrations_bp.route("/<provider>/sync", methods=["POST"])
@login_required
def sync(provider):
    integration = Integration.query.filter_by(
        user_id=current_user.id, provider=provider
    ).first()
    if not integration or not integration.access_token:
        return jsonify({"error": "Integration not connected"}), 400

    svc = _get_service(provider)
    if not _refresh_if_needed(integration, svc):
        return jsonify(
            {"error": "Token expired. Please reconnect.", "reconnect_required": True}
        ), 401

    integration.sync_status = "syncing"
    db.session.commit()

    try:
        sync_result = svc.sync_data(integration.access_token)
        if sync_result.get("provider_user_id"):
            integration.provider_user_id = sync_result["provider_user_id"]
        if sync_result.get("provider_username"):
            integration.provider_username = sync_result["provider_username"]
        if sync_result.get("provider_email"):
            integration.provider_email = sync_result["provider_email"]
        if sync_result.get("provider_data"):
            existing = integration.provider_data or {}
            if isinstance(sync_result["provider_data"], dict):
                existing.update(sync_result["provider_data"])
            integration.provider_data = existing

        integration.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)
        integration.sync_status = "connected"
        integration.sync_error = None
        _record_sync_history(integration, "success", "Sync completed")
        db.session.commit()

        try:
            sync_profile_from_integration(integration, current_user.id)
        except Exception as pe:
            logger.warning("Profile sync failed after sync for %s: %s", provider, pe)

        try:
            from app.core.integration import on_profile_changed
            on_profile_changed(current_user.id)
        except Exception as e:
            logger.warning("Integration hook failed after sync: %s", e)

        return jsonify(
            {"message": "Sync completed", "integration": integration.to_dict()}
        ), 200
    except Exception as e:
        db.session.rollback()
        integration.sync_status = "sync_failed"
        integration.sync_error = str(e)
        _record_sync_history(integration, "failed", str(e))
        db.session.commit()
        logger.error("Sync failed for %s: %s", provider, e)
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500


# ── Get data ───────────────────────────────────────────────


@integrations_bp.route("/<provider>/data", methods=["GET"])
@login_required
def get_data(provider):
    integration = Integration.query.filter_by(
        user_id=current_user.id, provider=provider
    ).first()
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    return jsonify({"integration": integration.to_dict()}), 200


# ── LinkedIn fallback: import from profile URL ─────────────


@integrations_bp.route("/linkedin/import", methods=["POST"])
@login_required
def linkedin_import():
    data = request.get_json(silent=True) or {}
    profile_url = data.get("profile_url", "").strip()
    if not profile_url or "linkedin.com/in/" not in profile_url:
        return jsonify({"error": "Valid LinkedIn profile URL is required"}), 400

    result = import_from_profile_url(profile_url)
    integration = _get_integration(current_user.id, "linkedin")
    integration.provider_user_id = result.get("provider_user_id", "")
    integration.provider_username = result.get("provider_username", "")
    integration.sync_status = "connected"
    integration.provider_data = result.get("provider_data", {})
    integration.connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    integration.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    from app.career.models import CareerTimelineEvent
    event = CareerTimelineEvent(
        user_id=current_user.id,
        event_type="integration",
        title="LinkedIn Profile Imported",
        description="Imported profile data from LinkedIn URL",
        event_date=datetime.now(timezone.utc),
        importance=3,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(
        {"message": "LinkedIn profile imported", "integration": integration.to_dict()}
    ), 200
