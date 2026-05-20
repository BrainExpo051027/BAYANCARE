import os
from dotenv import load_dotenv

# Find the .env file at the root of the project (3 directories up)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
load_dotenv(dotenv_path=env_path)

class Config:
    # Secret key - MUST be set via environment variable for production
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Generate a random key for development only (will change on restart)
        import secrets
        SECRET_KEY = secrets.token_hex(32)
        print("WARNING: Using randomly generated SECRET_KEY. Set SECRET_KEY environment variable for production.")
    # Database - MUST be set via environment variable for production
    # For development, you can set: postgresql://USERNAME:PASSWORD@localhost/bayancare_db
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        # Allow development without env var, but warn
        import socket
        try:
            # Try to connect to local PostgreSQL with common defaults
            SQLALCHEMY_DATABASE_URI = "postgresql://postgres:102705@localhost/bayancare_db"
            print("WARNING: Using fallback local database. Set DATABASE_URL environment variable for production.")
        except:
            raise ValueError("DATABASE_URL environment variable must be set (e.g., postgresql://user:pass@localhost/dbname)")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Session configuration
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "flask_session")
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "bayancare:"
    # Mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@bayancare.local")
    # Notification test routes: disabled in production unless explicitly enabled
    ENABLE_NOTIFICATION_TEST_ROUTES = os.environ.get(
        "ENABLE_NOTIFICATION_TEST_ROUTES", ""
    ).lower() in ("true", "on", "1")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 3 * 1024 * 1024))
    MAX_ANNOUNCEMENT_IMAGE_BYTES = int(
        os.environ.get("MAX_ANNOUNCEMENT_IMAGE_BYTES", 2 * 1024 * 1024)
    )
    ALLOWED_TEST_EMAIL_DOMAINS = [
        d.strip().lower()
        for d in os.environ.get(
            "ALLOWED_TEST_EMAIL_DOMAINS", "bayancare.local,localhost"
        ).split(",")
        if d.strip()
    ]
