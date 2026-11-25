"""Admin authentication and CSRF protection.

- Admins log in with a username and password; only a salted hash is stored (werkzeug).
- The logged-in admin id is kept in Flask's signed session cookie.
- Every state-changing request (POST, PUT, PATCH, DELETE) must carry the CSRF token
  stored in the session: forms send it as a hidden field, JavaScript as a header.
"""
import functools
import hmac
import secrets

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

from db import get_db

bp = Blueprint("auth", __name__)

UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


# ---------------------------------------------------------------- CSRF

def csrf_token():
    """Return this session's CSRF token, creating it on first use (exposed to templates)."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    """before_request hook: reject unsafe requests without a valid token."""
    if request.method not in UNSAFE_METHODS:
        return None
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    # compare_digest avoids leaking information through response timing
    if not expected or not hmac.compare_digest(sent, expected):
        if request.path.startswith("/api/"):
            return jsonify(error="Missing or invalid CSRF token."), 400
        abort(400, description="Your session expired or the form was tampered with. Reload the page and try again.")
    return None


# ---------------------------------------------------------------- session

def load_admin():
    """before_request hook: make the logged-in admin (or None) available as g.admin."""
    admin_id = session.get("admin_id")
    g.admin = None
    if admin_id is not None:
        g.admin = get_db().execute("SELECT id, username FROM admins WHERE id = ?", (admin_id,)).fetchone()


def admin_required(view):
    """Decorator for admin-only views. Pages redirect to login; the API answers 401."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.admin is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Admin login required."), 401
            flash("Log in as admin to do that.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def _safe_next(target):
    """Only follow relative redirects after login, to avoid open-redirect attacks."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = get_db().execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        # Same message for unknown user and wrong password: no hint about which one failed.
        if admin is None or not check_password_hash(admin["password_hash"], password):
            error = "Wrong username or password."
        else:
            session.clear()  # new session on login: protects against session fixation
            session["admin_id"] = admin["id"]
            flash(f"Welcome back, {admin['username']}.", "success")
            return redirect(_safe_next(request.args.get("next")))
    return render_template("login.html", error=error, username=username), (401 if error else 200)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("index"))
