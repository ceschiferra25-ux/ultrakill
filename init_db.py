"""Rebuild the database from scratch: `python init_db.py`.

Drops every table, recreates the schema and loads the starting entries plus the admin
account (ADMIN_USERNAME / ADMIN_PASSWORD environment variables, see README).
"""
from app import create_app
from db import init_db

if __name__ == "__main__":
    with create_app().app_context():
        init_db()
    print("Database initialised with the starting entries and the admin account.")
