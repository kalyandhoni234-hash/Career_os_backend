from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, oauth, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True, origins=[app.config["FRONTEND_URL"]])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    oauth.init_app(app)
    limiter.init_app(app)

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
    from app.coach.models import CoachMessage  # noqa: F401
    from app.jobs.models import Job  # noqa: F401
    from app.career.models import (  # noqa: F401
        CareerProfile,
        CareerGoal,
        Roadmap,
        RoadmapNode,
        LearningProgress,
        SkillGraph,
        CareerReport,
        CareerTimelineEvent,
        AIRecommendation,
        CareerScoreSnapshot,
        UserEducation,
        UserSkill,
        UserInterest,
        UserLanguage,
        SocialLink,
        ResumeFile,
        UserPreference,
        TimelineTag,
        TimelineAttachment,
    )
    from app.opportunities.models import (  # noqa: F401
        Opportunity,
        CompanyProfile,
        SavedOpportunity,
        OpportunityMatchScore,
        OpportunitySkillGap,
        SalaryInsight,
        MarketTrend,
        InterviewPack,
        ResumeVersionByCompany,
    )
    from app.agents.models import CareerAgent, AgentTask  # noqa: F401
    from app.intelligence.models import (  # noqa: F401
        CanonicalProject,
        CanonicalExperience,
        CanonicalCertificate,
        CareerEvent,
    )
    from app.recruiters.models import (  # noqa: F401
        Recruiter,
        Company,
        JobPost,
        SavedCandidate,
        TalentPipeline,
        CandidateView,
        InterviewInvite,
        RecruiterNotification,
    )
    from app.integrations.models import Integration  # noqa: F401
    import importlib

    ImportRecord = importlib.import_module("app.import.models").ImportRecord  # noqa: F401 F841

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth.routes import auth_bp
    from app.users.routes import users_bp
    from app.resume.routes import resume_bp
    from app.jobs.routes import jobs_bp
    from app.coach.routes import coach_bp
    from app.career.routes import career_bp
    from app.career.profile_routes import profile_bp
    from app.career.timeline_routes import timeline_bp
    from app.opportunities.routes import opportunities_bp
    from app.agents.routes import agents_bp
    from app.recruiters.routes import recruiters_bp

    import_bp = importlib.import_module("app.import.routes").import_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(coach_bp, url_prefix="/api/coach")
    app.register_blueprint(career_bp, url_prefix="/api/career")
    app.register_blueprint(profile_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(opportunities_bp, url_prefix="/api/opportunities")
    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(import_bp, url_prefix="/api/import")
    from app.integrations.routes import integrations_bp

    app.register_blueprint(integrations_bp)

    app.register_blueprint(recruiters_bp, url_prefix="/api/recruiters")

    from app.onboarding.routes import onboarding_bp

    app.register_blueprint(onboarding_bp)

    from app.intelligence.routes import intelligence_bp

    app.register_blueprint(intelligence_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized — please log in again"}), 401

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
