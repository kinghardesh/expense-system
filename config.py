"""Configuration objects.

Settings are read from environment variables so the same code runs unchanged in
development (SQLite) and production (PostgreSQL on Render). Never hard-code
secrets here.
"""
import os

from werkzeug.security import generate_password_hash


def _normalise_db_url(url: str) -> str:
    """Render/Heroku expose Postgres URLs as ``postgres://`` but SQLAlchemy 1.4+
    requires ``postgresql://``. Patch it so deployment 'just works'."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # --- Core ---------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

    SQLALCHEMY_DATABASE_URI = _normalise_db_url(
        os.environ.get("DATABASE_URL", "sqlite:///expense.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Admin credentials --------------------------------------------------
    # The system has a single admin account. The username comes straight from
    # the environment. The password is never stored in plain text: we accept
    # either a pre-computed hash (ADMIN_PASSWORD_HASH, preferred for prod) or a
    # raw password (ADMIN_PASSWORD, convenient for dev) which we hash at startup.
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")

    _password_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    if not _password_hash:
        _raw = os.environ.get("ADMIN_PASSWORD", "admin123")
        _password_hash = generate_password_hash(_raw)
    ADMIN_PASSWORD_HASH = _password_hash

    # --- Session hardening --------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only send the cookie over HTTPS in production. Controlled by env so local
    # http://localhost development still works.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # --- Pagination / display ----------------------------------------------
    PER_PAGE = int(os.environ.get("PER_PAGE", 15))


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
