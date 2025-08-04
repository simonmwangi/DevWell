import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv("secrets.env")


class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get("SECRET_KEY") or "devwell-secret-key-123"

    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "devwell.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # File upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # AI Model Configuration
    MODEL_CACHE_DIR = os.path.join(basedir, "ai_models")

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = os.environ.get("MAIL_PORT")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL")
    # MAIL_USE_TLS = bool(os.environ.get("MAIL_USE_TLS"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    @staticmethod
    def init_app(app):
        # Ensure upload directory exists
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(Config.MODEL_CACHE_DIR, exist_ok=True)
