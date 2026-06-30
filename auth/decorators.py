"""Authentication helpers and route guards."""
from functools import wraps

from flask import session, redirect, url_for, flash, current_app
from werkzeug.security import check_password_hash


def verify_credentials(username: str, password: str) -> bool:
    """Return True iff the supplied username/password match the configured
    admin account. Uses a constant-time hash comparison for the password."""
    cfg = current_app.config
    if username != cfg["ADMIN_USERNAME"]:
        return False
    return check_password_hash(cfg["ADMIN_PASSWORD_HASH"], password)


def login_required(f):
    """Block access unless the admin is signed in."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=_safe_next()))
        return f(*args, **kwargs)
    return wrapped


def _safe_next():
    """Capture the current path so we can redirect back after login."""
    from flask import request
    return request.full_path if request.endpoint != "auth.login" else None
