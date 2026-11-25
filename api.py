"""JSON API used by the JavaScript front end (static/js/main.js).

| Method | URL                              | Who      | Purpose                         |
|--------|----------------------------------|----------|---------------------------------|
| GET    | /api/entries                     | everyone | list / filter entries           |
| GET    | /api/entries/<id>                | everyone | one entry                       |
| PUT    | /api/entries/<id>                | admin    | replace an entry's data         |
| DELETE | /api/entries/<id>                | admin    | delete an entry and its tips    |
| GET    | /api/entries/<id>/comments       | everyone | list the tips of an entry       |
| POST   | /api/entries/<id>/comments       | everyone | add a tip                       |
| DELETE | /api/comments/<id>               | admin    | delete a tip (moderation)       |

Unsafe methods also need the X-CSRF-Token header (see auth.check_csrf).
"""
from flask import Blueprint, jsonify, request

import models
from auth import admin_required

bp = Blueprint("api", __name__, url_prefix="/api")


def _not_found(what="Entry"):
    return jsonify(error=f"{what} not found."), 404


@bp.get("/entries")
def list_entries():
    rows = models.search_entries(
        category=request.args.get("category", "all").lower(),
        faction=request.args.get("faction", "all"),
        search=request.args.get("search", "").strip(),
        secret_only=request.args.get("secret") == "1",
    )
    return jsonify(count=len(rows), entries=[models.entry_to_dict(r) for r in rows])


@bp.get("/entries/<int:entry_id>")
def get_entry(entry_id):
    row = models.get_entry(entry_id)
    return jsonify(models.entry_to_dict(row)) if row else _not_found()


@bp.put("/entries/<int:entry_id>")
@admin_required
def update_entry(entry_id):
    if models.get_entry(entry_id) is None:
        return _not_found()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Send the entry as a JSON object."), 400
    data, errors = models.validate_entry(payload, entry_id=entry_id)
    if errors:
        return jsonify(error="Invalid data.", fields=errors), 422
    models.update_entry(entry_id, data)
    return jsonify(models.entry_to_dict(models.get_entry(entry_id)))


@bp.delete("/entries/<int:entry_id>")
@admin_required
def delete_entry(entry_id):
    if not models.delete_entry(entry_id):
        return _not_found()
    return "", 204


@bp.get("/entries/<int:entry_id>/comments")
def list_comments(entry_id):
    if models.get_entry(entry_id) is None:
        return _not_found()
    return jsonify([models.comment_to_dict(c) for c in models.list_comments(entry_id)])


@bp.post("/entries/<int:entry_id>/comments")
def add_comment(entry_id):
    if models.get_entry(entry_id) is None:
        return _not_found()
    payload = request.get_json(silent=True) or {}
    data, errors = models.validate_comment(payload)
    if errors:
        return jsonify(error="Invalid tip.", fields=errors), 422
    comment = models.create_comment(entry_id, data)
    return jsonify(models.comment_to_dict(comment)), 201


@bp.delete("/comments/<int:comment_id>")
@admin_required
def delete_comment(comment_id):
    if not models.delete_comment(comment_id):
        return _not_found("Tip")
    return "", 204
