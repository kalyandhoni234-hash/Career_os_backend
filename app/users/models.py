from app.extensions import db

class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    education = db.Column(db.String(255))
    degree = db.Column(db.String(255))
    graduation_year = db.Column(db.Integer)
    country = db.Column(db.String(100))
    preferred_roles = db.Column(db.JSON)
    skills = db.Column(db.JSON)
    experience = db.Column(db.Text)
    languages = db.Column(db.JSON)
    interests = db.Column(db.JSON)
    preferred_locations = db.Column(db.JSON)
    salary_expectation = db.Column(db.String(100))
