"""Data access and validation for entries and comments.

Both the HTML pages (app.py) and the JSON API (api.py) go through these functions,
so the rules are written once. Every query uses ? placeholders: user input is never
concatenated into SQL, which prevents SQL injection.
"""
import os
import re

from flask import current_app, url_for
from werkzeug.utils import secure_filename

from db import CATEGORIES, FACTIONS, get_db

# Length limits shared by server-side validation and the HTML maxlength attributes.
LIMITS = {
    "name": 80,
    "lore": 600,
    "attack_patterns": 600,
    "weaknesses": 600,
    "strategies": 600,
    "author": 40,
    "message": 1000,
}
TEXT_FIELDS = ("lore", "attack_patterns", "weaknesses", "strategies")
IMAGE_EXTENSIONS = (".webp", ".png", ".jpg", ".jpeg", ".gif")


# ---------------------------------------------------------------- helpers

def slugify(name):
    """'Gabriel, Judge of Hell' -> 'gabriel-judge-of-hell' (used for image file names)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def faction_slug(faction):
    """'Prime Souls' -> 'prime-souls' (used for faction icon file names)."""
    return slugify(faction)


def image_url(entry):
    """Return the URL of the entry's picture, or None if no picture file exists.

    Looks first at the file name stored in the database, then at
    static/images/enemies/<slug>.<ext>, so pictures can be added just by dropping files.
    """
    folder = current_app.config["ENEMY_IMAGE_FOLDER"]
    candidates = [entry["image"]] if entry["image"] else []
    candidates += [slugify(entry["name"]) + ext for ext in IMAGE_EXTENSIONS]
    for filename in candidates:
        if os.path.isfile(os.path.join(folder, filename)):
            return url_for("static", filename=f"images/enemies/{filename}")
    return None


def entry_to_dict(row):
    """Convert a database row to a JSON-friendly dict (used by the API)."""
    data = dict(row)
    data["is_cyber_grind"] = bool(data["is_cyber_grind"])
    data["is_secret"] = bool(data["is_secret"])
    data["image_url"] = image_url(row)
    data["faction_icon"] = url_for("static", filename=f"images/factions/{faction_slug(row['faction'])}.svg")
    data["url"] = url_for("entry_detail", entry_id=row["id"])
    return data


def comment_to_dict(row):
    return dict(row)


# ---------------------------------------------------------------- entries

def search_entries(category="all", faction="all", search="", secret_only=False):
    """Return entries matching the filters, sorted by faction and name."""
    query = "SELECT * FROM entries WHERE 1=1"
    params = []
    if category in CATEGORIES:
        query += " AND category = ?"
        params.append(category)
    if faction in FACTIONS:
        query += " AND faction = ?"
        params.append(faction)
    if secret_only:
        query += " AND is_secret = 1"
    if search:
        query += " AND (name LIKE ? OR lore LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY faction ASC, name ASC"
    return get_db().execute(query, params).fetchall()


def get_entry(entry_id):
    return get_db().execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()


def faction_counts():
    """{'Husks': 9, ...} including factions with zero entries."""
    rows = get_db().execute("SELECT faction, COUNT(*) AS n FROM entries GROUP BY faction").fetchall()
    counts = {f: 0 for f in FACTIONS}
    counts.update({r["faction"]: r["n"] for r in rows})
    return counts


def stats():
    """Totals shown on the home page."""
    row = get_db().execute(
        """SELECT COUNT(*) AS total,
                  SUM(category = 'boss') AS bosses,
                  SUM(is_secret = 1) AS secrets,
                  SUM(is_cyber_grind = 1) AS cyber_grind
           FROM entries"""
    ).fetchone()
    comments = get_db().execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    return {**{k: row[k] or 0 for k in row.keys()}, "comments": comments}


def validate_entry(form, entry_id=None):
    """Check submitted entry data. Returns (clean_data, errors_by_field).

    `form` can be request.form or a JSON dict. Checkboxes arrive as "1"/"on"/True.
    """
    data, errors = {}, {}

    data["name"] = str(form.get("name", "")).strip()
    if not data["name"]:
        errors["name"] = "Name is required."
    elif len(data["name"]) > LIMITS["name"]:
        errors["name"] = f"Name must be at most {LIMITS['name']} characters."
    else:
        clash = get_db().execute(
            "SELECT id FROM entries WHERE lower(name) = lower(?) AND id != ?",
            (data["name"], entry_id or -1),
        ).fetchone()
        if clash:
            errors["name"] = "An entry with this name already exists."

    data["category"] = str(form.get("category", "")).lower()
    if data["category"] not in CATEGORIES:
        errors["category"] = "Choose enemy or boss."

    data["faction"] = str(form.get("faction", ""))
    if data["faction"] not in FACTIONS:
        errors["faction"] = "Choose one of the six factions."

    for flag in ("is_cyber_grind", "is_secret"):
        data[flag] = 1 if form.get(flag) in ("1", "on", "true", True, 1) else 0

    labels = {"lore": "Lore", "attack_patterns": "Attack patterns",
              "weaknesses": "Weaknesses", "strategies": "Strategies"}
    for field in TEXT_FIELDS:
        data[field] = str(form.get(field, "")).strip()
        if not data[field]:
            errors[field] = f"{labels[field]} is required."
        elif len(data[field]) > LIMITS[field]:
            errors[field] = f"{labels[field]} must be at most {LIMITS[field]} characters."

    return data, errors


def create_entry(data):
    cur = get_db().execute(
        """INSERT INTO entries (name, category, faction, is_cyber_grind, is_secret,
                                lore, attack_patterns, weaknesses, strategies, image)
           VALUES (:name, :category, :faction, :is_cyber_grind, :is_secret,
                   :lore, :attack_patterns, :weaknesses, :strategies, :image)""",
        {"image": None, **data},
    )
    get_db().commit()
    return cur.lastrowid


def update_entry(entry_id, data):
    fields = ["name", "category", "faction", "is_cyber_grind", "is_secret", *TEXT_FIELDS]
    if "image" in data:
        fields.append("image")
    assignments = ", ".join(f"{f} = :{f}" for f in fields)  # field names are fixed, not user input
    get_db().execute(
        f"UPDATE entries SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
        {**data, "id": entry_id},
    )
    get_db().commit()


def delete_entry(entry_id):
    """Delete an entry; its comments go with it (ON DELETE CASCADE)."""
    cur = get_db().execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    get_db().commit()
    return cur.rowcount > 0


def save_image(file_storage, entry_name):
    """Store an uploaded picture as static/images/enemies/<slug>.<ext>.

    Returns (filename, error). Only image extensions are accepted; the size limit is
    enforced by Flask through MAX_CONTENT_LENGTH.
    """
    if not file_storage or not file_storage.filename:
        return None, None
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return None, "Image must be a .webp, .png, .jpg or .gif file."
    filename = slugify(entry_name) + ext
    file_storage.save(os.path.join(current_app.config["ENEMY_IMAGE_FOLDER"], filename))
    return filename, None


# ---------------------------------------------------------------- comments

def list_comments(entry_id):
    return get_db().execute(
        "SELECT * FROM comments WHERE entry_id = ? ORDER BY created_at DESC, id DESC",
        (entry_id,),
    ).fetchall()


def validate_comment(form):
    data = {
        "author": str(form.get("author", "")).strip(),
        "message": str(form.get("message", "")).strip(),
    }
    errors = {}
    if not data["author"]:
        errors["author"] = "Nickname is required."
    elif len(data["author"]) > LIMITS["author"]:
        errors["author"] = f"Nickname must be at most {LIMITS['author']} characters."
    if not data["message"]:
        errors["message"] = "Write a tip before sending."
    elif len(data["message"]) > LIMITS["message"]:
        errors["message"] = f"Tip must be at most {LIMITS['message']} characters."
    return data, errors


def create_comment(entry_id, data):
    db = get_db()
    cur = db.execute(
        "INSERT INTO comments (entry_id, author, message) VALUES (?, ?, ?)",
        (entry_id, data["author"], data["message"]),
    )
    db.commit()
    return db.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone()


def delete_comment(comment_id):
    cur = get_db().execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    get_db().commit()
    return cur.rowcount > 0
