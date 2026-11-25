import sqlite3
from flask import Flask, render_template, request, redirect, url_for, abort

app = Flask(__name__)
DATABASE = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/entries")
def entries():
    category = request.args.get("category", "all").lower()
    faction = request.args.get("faction", "all")
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM entries WHERE 1=1"
    params = []

    if category in ("boss", "enemy"):
        query += " AND category = ?"
        params.append(category)

    if faction != "all":
        query += " AND faction = ?"
        params.append(faction)

    if search:
        query += " AND (name LIKE ? OR lore LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY faction ASC, name ASC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    page_title = "ALL ENEMIES // DATABASE"
    if faction != "all":
        page_title = f"CATEGORY // {faction.upper()}"

    return render_template(
        "entries.html",
        entries=rows,
        category=category,
        faction=faction,
        search=search,
        page_title=page_title,
        form_action=url_for("entries")
    )


@app.route("/categories")
def categories():
    conn = get_db_connection()
    factions_order = ["Husks", "Machines", "Demons", "Angels", "Other", "Prime Souls"]
    descriptions = {
        "Husks": "Manifestazioni fisiche delle anime dei dannati nell'Inferno, la cui forma dipende dalla volontà e dalla fama in vita.",
        "Machines": "Unità robotiche alimentate a sangue costruite dall'umanità durante la Grande Guerra e la Nuova Pace.",
        "Demons": "Creature nate direttamente dalla materia infernale e rivestite da gusci di pietra scolpita.",
        "Angels": "Entità celesti del Paradiso incaricate di sorvegliare i gironi dell'Inferno e mantenere l'ordine divino.",
        "Other": "Costrutti organici come Flesh Prison/Panopticon e anomalie segrete nascoste nei livelli.",
        "Prime Souls": "Anime umane dalla volontà così immensa da manifestarsi senza alcun corpo fisico."
    }

    category_cards = []
    for f in factions_order:
        count = conn.execute("SELECT COUNT(*) FROM entries WHERE faction = ?", (f,)).fetchone()[0]
        category_cards.append({
            "name": f,
            "count": count,
            "description": descriptions.get(f, "")
        })

    conn.close()
    return render_template("categories.html", categories=category_cards)


@app.route("/bosses")
def bosses():
    faction = request.args.get("faction", "all")
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM entries WHERE category = 'boss'"
    params = []

    if faction != "all":
        query += " AND faction = ?"
        params.append(faction)

    if search:
        query += " AND (name LIKE ? OR lore LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY faction ASC, name ASC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "entries.html",
        entries=rows,
        category="boss",
        faction=faction,
        search=search,
        page_title="BOSSES // SPECIAL ENCOUNTERS",
        form_action=url_for("bosses")
    )


@app.route("/secrets")
def secrets():
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM entries WHERE is_secret = 1"
    params = []

    if search:
        query += " AND (name LIKE ? OR lore LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY name ASC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "entries.html",
        entries=rows,
        category="boss",
        faction="Other",
        search=search,
        page_title="SECRET ENCOUNTERS // HIDDEN ENTITIES",
        form_action=url_for("secrets")
    )


@app.route("/entry/<int:entry_id>", methods=["GET", "POST"])
def entry_detail(entry_id):
    conn = get_db_connection()
    entry = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()

    if entry is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        author = request.form.get("author", "").strip()
        message = request.form.get("message", "").strip()
        if author and message:
            conn.execute(
                "INSERT INTO comments (entry_id, author, message) VALUES (?, ?, ?)",
                (entry_id, author, message),
            )
            conn.commit()
        conn.close()
        return redirect(url_for("entry_detail", entry_id=entry_id))

    comments = conn.execute(
        "SELECT * FROM comments WHERE entry_id = ? ORDER BY created_at DESC",
        (entry_id,),
    ).fetchall()
    conn.close()

    return render_template("detail.html", entry=entry, comments=comments)


@app.route("/submit", methods=["GET", "POST"])
def submit_entry():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "enemy").lower()
        faction = request.form.get("faction", "Machines")
        is_cyber_grind = 1 if request.form.get("is_cyber_grind") == "1" else 0
        is_secret = 1 if request.form.get("is_secret") == "1" else 0
        lore = request.form.get("lore", "").strip()
        attack_patterns = request.form.get("attack_patterns", "").strip()
        weaknesses = request.form.get("weaknesses", "").strip()
        strategies = request.form.get("strategies", "").strip()

        if name and lore and attack_patterns and weaknesses and strategies:
            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO entries (name, category, faction, is_cyber_grind, is_secret, lore, attack_patterns, weaknesses, strategies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, category, faction, is_cyber_grind, is_secret, lore, attack_patterns, weaknesses, strategies),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("entries"))

    return render_template("submit.html")


if __name__ == "__main__":
    app.run(debug=True)