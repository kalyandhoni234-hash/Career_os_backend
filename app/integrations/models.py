import secrets
from datetime import datetime, timezone
from app.extensions import db


class OAuthState(db.Model):
    __tablename__ = "oauth_states"

    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", backref=db.backref("oauth_states", lazy="dynamic"))

    @classmethod
    def create(cls, user_id: int, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None)
        from datetime import timedelta

        expires_at += timedelta(minutes=10)
        record = cls(
            state=state, user_id=user_id, provider=provider, expires_at=expires_at
        )
        db.session.add(record)
        db.session.commit()
        return state

    @classmethod
    def consume(cls, state: str) -> tuple[int, str] | None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        record = cls.query.filter(
            cls.state == state,
            cls.expires_at > now,
        ).first()
        if not record:
            return None
        user_id = record.user_id
        provider = record.provider
        db.session.delete(record)
        db.session.commit()
        return (user_id, provider)

    @classmethod
    def cleanup_expired(cls):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls.query.filter(cls.expires_at <= now).delete()
        db.session.commit()


class Integration(db.Model):
    __tablename__ = "integrations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    provider_user_id = db.Column(db.String(255), nullable=True)
    provider_username = db.Column(db.String(255), nullable=True)
    provider_email = db.Column(db.String(255), nullable=True)
    connected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_sync_at = db.Column(db.DateTime, nullable=True)
    sync_status = db.Column(db.String(20), default="not_connected")
    sync_error = db.Column(db.Text, nullable=True)
    provider_data = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("integrations", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "connected": self.sync_status not in ("not_connected", "connection_error"),
            "sync_status": self.sync_status,
            "sync_error": self.sync_error,
            "provider_user_id": self.provider_user_id,
            "provider_username": self.provider_username,
            "provider_email": self.provider_email,
            "connected_at": self.connected_at.isoformat()
            if self.connected_at
            else None,
            "last_sync_at": self.last_sync_at.isoformat()
            if self.last_sync_at
            else None,
            "provider_data": self.provider_data or {},
        }
