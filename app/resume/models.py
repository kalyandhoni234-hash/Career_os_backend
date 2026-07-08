from datetime import datetime
from app.extensions import db

class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    summary = db.Column(db.Text)

    experience = db.Column(db.JSON)   # list of {company, role, start, end, bullets}
    education = db.Column(db.JSON)    # list of {school, degree, start, end}
    projects = db.Column(db.JSON)     # list of {name, description, link}
    skills = db.Column(db.JSON)       # list of strings

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
