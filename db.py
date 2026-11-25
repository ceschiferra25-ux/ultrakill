"""Database layer: one SQLite connection per request, schema creation and seeding."""
import os
import sqlite3

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

# Allowed values, shared by validation, templates and the API.
FACTIONS = ("Husks", "Machines", "Demons", "Angels", "Other", "Prime Souls")
CATEGORIES = ("enemy", "boss")

FACTION_DESCRIPTIONS = {
    "Husks": "Physical manifestations of the souls of the damned; their form depends on the will and fame they had in life.",
    "Machines": "Blood-powered robotic units built by mankind during the Great War and the New Peace.",
    "Demons": "Creatures born directly from the matter of Hell and wrapped in shells of carved stone.",
    "Angels": "Celestial beings from Heaven, tasked with watching over the layers of Hell and keeping divine order.",
    "Other": "Organic constructs such as the Flesh Prison and Panopticon, plus secret anomalies hidden in the levels.",
    "Prime Souls": "Human souls whose will is so immense that they manifest without any physical body.",
}


def get_db():
    """Return the request's database connection, opening it on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
        g.db.execute("PRAGMA foreign_keys = ON")  # needed for ON DELETE CASCADE
    return g.db


def close_db(_error=None):
    """Close the connection at the end of the request (registered as teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(with_seed=True):
    """Create every table from schema.sql and optionally load the starting data."""
    db = get_db()
    schema_path = os.path.join(current_app.root_path, "schema.sql")
    with open(schema_path, encoding="utf-8") as schema:
        db.executescript(schema.read())

    if with_seed:
        from seed_data import ENTRIES  # imported here to keep app start-up light

        db.executemany(
            """INSERT INTO entries (name, category, faction, is_cyber_grind, is_secret,
                                    lore, attack_patterns, weaknesses, strategies)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ENTRIES,
        )

    # The admin account comes from environment variables so no real password lives in the code.
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "ultrakill-admin")
    db.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password)),
    )
    db.commit()


@click.command("init-db")
def init_db_command():
    """`flask --app app init-db`: rebuild the database with the starting data."""
    init_db()
    click.echo("Database initialised.")


def init_app(app):
    """Register the teardown hook and the CLI command on the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
