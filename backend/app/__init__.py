from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from app.config.config import Config
from app.extensions import db, bcrypt, login_manager, server_session, mail
from app.routes import auth_bp, announcement_bp, assessment_bp, referral_bp, profile_bp, notification_bp, recovery_bp, admin_bp, consultation_bp
from app.models.user import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend (local dev)
    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:5000",
            "http://localhost:5000",
        ],
    )

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    server_session.init_app(app)
    mail.init_app(app)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(announcement_bp, url_prefix="/api/announcements")
    app.register_blueprint(assessment_bp, url_prefix="/api/assessments")
    app.register_blueprint(referral_bp, url_prefix="/api/referrals")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(notification_bp, url_prefix="/api/notifications")
    app.register_blueprint(recovery_bp, url_prefix="/api/recovery")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(consultation_bp, url_prefix="/api/consultations")

    frontend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    frontend_pages = os.path.join(frontend_root, "pages")
    frontend_assets = os.path.join(frontend_root, "assets")

    @app.route("/")
    def index():
        return send_from_directory(frontend_pages, "index.html")

    @app.route("/pages/<path:filename>")
    def serve_pages(filename):
        return send_from_directory(frontend_pages, filename)

    @app.route("/<path:filename>")
    def serve_root_files(filename):
        # Allow direct access like /dashboard.html when frontend JS redirects there
        if filename.startswith("api/"):
            return ("", 404)
        return send_from_directory(frontend_pages, filename)

    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        return send_from_directory(frontend_assets, filename)

    @app.route("/favicon.ico")
    def favicon():
        return ("", 204)

    # Simple health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "BAYANCARE backend"}

    return app
