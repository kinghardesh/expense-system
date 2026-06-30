"""Login / logout routes for the single admin account."""
from urllib.parse import urlparse

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    current_app,
)

from auth.decorators import verify_credentials

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_url(target: str) -> bool:
    """Only allow relative redirects (same host) to prevent open-redirects."""
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == ""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("expenses.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if verify_credentials(username, password):
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            flash("Welcome back.", "success")

            nxt = request.form.get("next") or request.args.get("next")
            if nxt and _is_safe_url(nxt):
                return redirect(nxt)
            return redirect(url_for("expenses.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.app_context_processor
def inject_auth():
    """Expose login state to every template (navbar, sidebar)."""
    return {
        "logged_in": session.get("logged_in", False),
        "admin_username": session.get("username"),
    }
