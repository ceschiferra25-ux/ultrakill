"""ULTRAKILL Guide - Flask application: configuration, HTML pages and error handling.

Run with `python app.py` (development server on http://127.0.0.1:5000).
The JSON API lives in api.py, login and CSRF in auth.py, queries in models.py.
"""
import os
import secrets

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, url_for)

import api
import auth
import db
import models
from db import FACTION_DESCRIPTIONS, FACTIONS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(test_config=None):
    """Application factory: builds a configured app (tests pass their own config)."""
    app = Flask(__name__)
    app.config.update(
        # Set SECRET_KEY in the environment for real use; the random fallback logs everyone
        # out at every restart, which is acceptable for local development only.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE", os.path.join(BASE_DIR, "database.db")),
        ENEMY_IMAGE_FOLDER=os.path.join(BASE_DIR, "static", "images", "enemies"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # uploads larger than 2 MB get a 413 error
        SESSION_COOKIE_HTTPONLY=True,  # JavaScript cannot read the session cookie
        SESSION_COOKIE_SAMESITE="Lax",  # cookie not sent on cross-site POSTs
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.config["ENEMY_IMAGE_FOLDER"], exist_ok=True)

    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)
    app.before_request(auth.load_admin)
    app.before_request(auth.check_csrf)

    # First run: create and fill the database automatically.
    if not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            db.init_db()

    register_template_helpers(app)
    register_pages(app)
    register_error_handlers(app)

    @app.after_request
    def security_headers(response):
        """Browser-side protections: no sniffing, no framing, only our own scripts/styles."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    return app


def register_template_helpers(app):
    """Functions and constants available in every Jinja template."""
    @app.context_processor
    def inject():
        return {
            "csrf_token": auth.csrf_token,
            "FACTIONS": FACTIONS,
            "LIMITS": models.LIMITS,
            "faction_slug": models.faction_slug,
            "image_url": models.image_url,
            "is_admin": g.get("admin") is not None,
        }


def _listing(page_title, form_action, category="all", secret_only=False, show_type_filter=True):
    """Shared view for the three entry lists (all / bosses / secrets)."""
    category = request.args.get("category", category).lower()
    faction = request.args.get("faction", "all")
    search = request.args.get("search", "").strip()[:80]
    rows = models.search_entries(category, faction, search, secret_only)
    if faction in FACTIONS and not secret_only:
        page_title = f"{faction} // {page_title}"
    return render_template(
        "entries.html",
        entries=rows,
        category=category,
        faction=faction,
        search=search,
        page_title=page_title,
        form_action=form_action,
        show_type_filter=show_type_filter,
        secret_only=secret_only,
    )


def register_pages(app):
    """HTML pages. GET pages render templates; POST pages redirect after success (PRG)."""

    @app.route("/")
    def index():
        return render_template("index.html", stats=models.stats())

    @app.route("/entries")
    def entries():
        return _listing("All enemies", url_for("entries"))

    @app.route("/bosses")
    def bosses():
        return _listing("Bosses", url_for("bosses"), category="boss", show_type_filter=False)

    @app.route("/secrets")
    def secrets_page():
        return _listing("Secret encounters", url_for("secrets_page"), secret_only=True, show_type_filter=False)

    @app.route("/categories")
    def categories():
        counts = models.faction_counts()
        cards = [{"name": f, "count": counts[f], "description": FACTION_DESCRIPTIONS[f]} for f in FACTIONS]
        return render_template("categories.html", categories=cards)

    @app.route("/entry/<int:entry_id>", methods=["GET", "POST"])
    def entry_detail(entry_id):
        entry = models.get_entry(entry_id) or abort(404)
        errors, values = {}, {}
        # POST is the no-JavaScript fallback; with JS the form uses POST /api/.../comments.
        if request.method == "POST":
            values, errors = models.validate_comment(request.form)
            if not errors:
                models.create_comment(entry_id, values)
                flash("Tip posted. Thanks!", "success")
                return redirect(url_for("entry_detail", entry_id=entry_id, _anchor="tips"))
        status = 422 if errors else 200
        return render_template("detail.html", entry=entry, comments=models.list_comments(entry_id),
                               errors=errors, values=values), status

    @app.route("/entries/new", methods=["GET", "POST"])
    @auth.admin_required
    def new_entry():
        values, errors = {"category": "enemy", "faction": "Husks"}, {}
        if request.method == "POST":
            values, errors = models.validate_entry(request.form)
            if not errors:
                image, image_error = models.save_image(request.files.get("image"), values["name"])
                if image_error:
                    errors["image"] = image_error
                else:
                    entry_id = models.create_entry({**values, "image": image})
                    flash(f"{values['name']} added to the database.", "success")
                    return redirect(url_for("entry_detail", entry_id=entry_id))
        return render_template("entry_form.html", values=values, errors=errors, entry=None), (422 if errors else 200)

    @app.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
    @auth.admin_required
    def edit_entry(entry_id):
        entry = models.get_entry(entry_id) or abort(404)
        values, errors = dict(entry), {}
        if request.method == "POST":
            values, errors = models.validate_entry(request.form, entry_id=entry_id)
            if not errors:
                image, image_error = models.save_image(request.files.get("image"), values["name"])
                if image_error:
                    errors["image"] = image_error
                else:
                    if image:
                        values["image"] = image
                    models.update_entry(entry_id, values)
                    flash("Changes saved.", "success")
                    return redirect(url_for("entry_detail", entry_id=entry_id))
        return render_template("entry_form.html", values=values, errors=errors, entry=entry), (422 if errors else 200)

    @app.route("/entry/<int:entry_id>/delete", methods=["POST"])
    @auth.admin_required
    def delete_entry(entry_id):
        entry = models.get_entry(entry_id) or abort(404)
        models.delete_entry(entry_id)
        flash(f"{entry['name']} deleted.", "success")
        return redirect(url_for("entries"))

    @app.route("/comment/<int:comment_id>/delete", methods=["POST"])
    @auth.admin_required
    def delete_comment(comment_id):
        entry_id = request.form.get("entry_id", type=int)
        if not models.delete_comment(comment_id):
            abort(404)
        flash("Tip deleted.", "success")
        return redirect(url_for("entry_detail", entry_id=entry_id, _anchor="tips") if entry_id else url_for("index"))


ERROR_TEXT = {
    400: ("Bad request", "The request could not be processed."),
    404: ("Not found", "This page does not exist, or the entry was deleted."),
    405: ("Method not allowed", "This address does not accept that kind of request."),
    413: ("File too large", "Images can be at most 2 MB."),
    500: ("Server error", "Something broke on our side. Try again in a moment."),
}


def register_error_handlers(app):
    """Themed HTML error pages; JSON errors for /api/ addresses."""
    def handle(error):
        code = getattr(error, "code", 500) or 500
        title, text = ERROR_TEXT.get(code, ERROR_TEXT[500])
        if code == 400 and getattr(error, "description", None) and "session" in error.description:
            text = error.description
        if request.path.startswith("/api/"):
            return jsonify(error=title), code
        return render_template("error.html", code=code, title=title, text=text), code

    for code in ERROR_TEXT:
        app.register_error_handler(code, handle)


app = create_app()

if __name__ == "__main__":
    # debug stays off unless FLASK_DEBUG=1: the debugger must never run on a public server
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
