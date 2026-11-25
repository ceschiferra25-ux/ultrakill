"""Shared pytest fixtures: every test gets a fresh app with its own temporary database."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

ADMIN = {"username": "admin", "password": "test-password"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN["username"])
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN["password"])
    images = tmp_path / "images"
    images.mkdir()
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "test.db"),  # created and seeded by create_app
        "ENEMY_IMAGE_FOLDER": str(images),
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf(client):
    """Return a function giving the current session's CSRF token."""
    def token():
        client.get("/")  # rendering any page creates the token
        with client.session_transaction() as session:
            return session["csrf_token"]
    return token


@pytest.fixture
def admin(client, csrf):
    """Log the test client in as admin."""
    response = client.post("/login", data={**ADMIN, "csrf_token": csrf()})
    assert response.status_code == 302
    return client


@pytest.fixture
def entry_form(csrf):
    """Valid data for the new/edit entry form."""
    def build(**overrides):
        data = {
            "name": "Test Husk", "category": "enemy", "faction": "Husks", "is_cyber_grind": "1",
            "lore": "A test husk.", "attack_patterns": "Bites.", "weaknesses": "Everything.",
            "strategies": "Shoot it.", "csrf_token": csrf(),
        }
        data.update(overrides)
        return data
    return build
