from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, oauth

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from app.auth.models import User
    from app.users.models import Profile  # noqa: F401
    from app.resume.models import Resume  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth.routes import auth_bp
    from app.users.routes import users_bp
    from app.resume.routes import resume_bp
    from app.jobs.routes import jobs_bp
    from app.coach.routes import coach_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(coach_bp, url_prefix="/api/coach")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
