import traceback
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, oauth, limiter
from app import csrf


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

    @app.before_request
    def check_csrf():
        return csrf.protect()

    @app.after_request
    def attach_csrf_cookie(response):
        return csrf.set_csrf_cookie(response)

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from app.auth.models import User
    from app.users.models import Profile  # noqa: F401
    from app.resume.models import Resume, ResumeVersion  # noqa: F401
    from app.coach.models import CoachMessage  # noqa: F401
    from app.jobs.models import Job  # noqa: F401
    from app.career.models import (  # noqa: F401
        CareerProfile,
        CareerGoal,
        Roadmap,
        RoadmapNode,
        LessonProgress,
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
        UserPreference,
        TimelineTag,
        TimelineAttachment,
        ResumeFile,
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
    from app.relationships.models import Contact, Interaction  # noqa: F401
    from app.knowledge.models import InterviewRecord  # noqa: F401
    from app.engine.models import RuleExecutionLog  # noqa: F401
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

    from app.extension.routes import extension_bp

    app.register_blueprint(extension_bp)

    from app.onboarding.routes import onboarding_bp

    app.register_blueprint(onboarding_bp)

    from app.intelligence.routes import intelligence_bp

    app.register_blueprint(intelligence_bp)

    from app.relationships.routes import relationships_bp

    app.register_blueprint(relationships_bp, url_prefix="/api/relationships")

    from app.knowledge.routes import knowledge_bp

    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")

    from app.engine.routes import engine_bp

    app.register_blueprint(engine_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.errorhandler(401)
    def unauthorized(error):
        db.session.rollback()
        app.logger.warning("401 Unauthorized: %s", error)
        return jsonify({"error": "Unauthorized — please log in again", "code": "UNAUTHORIZED", "message": "Authentication required", "details": {}}), 401

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        tb = traceback.format_exc()
        app.logger.error("500 Internal Server Error: %s\n%s", error, tb)
        return jsonify({
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        }), 500

    @app.errorhandler(404)
    def not_found(error):
        db.session.rollback()
        app.logger.warning("404 Not Found: %s", error)
        return jsonify({"error": "Not found", "code": "NOT_FOUND", "message": "The requested resource was not found", "details": {}}), 404

    @app.errorhandler(429)
    def rate_limited(error):
        app.logger.warning("429 Rate Limit Exceeded: %s", error)
        return jsonify({"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests — please try again later", "details": {}}), 429

    @app.errorhandler(503)
    def service_unavailable(error):
        db.session.rollback()
        app.logger.warning("503 Service Unavailable: %s", error)
        return jsonify({"error": "Service unavailable", "code": "SERVICE_UNAVAILABLE", "message": "Service temporarily unavailable — please try again later", "details": {}}), 503

    from app.resume.pdf_engine import get_status as _pdf_status

    _pdf = _pdf_status()
    if _pdf["available"]:
        app.logger.info("PDF engine: WeasyPrint (native libs OK)")
    else:
        app.logger.warning(
            "PDF engine: WeasyPrint unavailable (%s). "
            "PDF export endpoints will return 503 errors. "
            "See /api/resume/pdf-health for details.",
            _pdf["error"],
        )

    # Start background rule engine scheduler once
    if app.config.get("SCHEDULER_ENABLED", True):
        _sched_started = getattr(app, "_scheduler_started", False)
        if not _sched_started:
            app._scheduler_started = True
            from app.engine.scheduler import init_scheduler

            try:
                init_scheduler(app)
            except Exception as e:
                app.logger.warning("Background scheduler failed to start: %s", e)

    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            db.session.rollback()
        elif db.session.is_active is False:
            db.session.rollback()
        db.session.remove()

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/system/version")
    def system_version():
        return jsonify({"version": "0.1.0", "build": "", "name": "Career OS"})

    return app
