from datetime import datetime, timezone
from app.extensions import db


class ImportRecord(db.Model):
    __tablename__ = "import_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="processing")
    raw_data = db.Column(db.JSON)
    normalized_data = db.Column(db.JSON)
    confidence_scores = db.Column(db.JSON)
    import_version = db.Column(db.String(20), default="1.0")
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="import_records")
