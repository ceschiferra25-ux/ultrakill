"""HTML pages: rendering, filters, forms, admin-only views and error pages."""
import io

import pytest


@pytest.mark.parametrize("path", ["/", "/entries", "/bosses", "/secrets", "/categories", "/entry/1", "/login"])
def test_public_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"ULTRAKILL" in response.data


def test_home_shows_statistics(client):
    assert b"41 ENTRIES LOADED" in client.get("/").data


def test_faction_filter(client):
    page = client.get("/entries?faction=Angels").data.decode()
    assert "Virtue" in page and "Filth" not in page


def test_type_filter(client):
    page = client.get("/entries?category=boss").data.decode()
    assert "Minos Prime" in page and "Filth" not in page


def test_search_matches_name_and_lore(client):
    assert "Leviathan" in client.get("/entries?search=serpent").data.decode()


def test_bosses_page_lists_only_bosses(client):
    page = client.get("/bosses").data.decode()
    assert "Sisyphus Prime" in page and "Stray" not in page


def test_secrets_page_lists_only_secrets(client):
    page = client.get("/secrets").data.decode()
    assert "Something Wicked" in page and "V2" not in page


def test_unknown_entry_gives_themed_404(client):
    response = client.get("/entry/9999")
    assert response.status_code == 404
    assert b"Back to home" in response.data


def test_security_headers_present(client):
    headers = client.get("/").headers
    assert headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in headers["Content-Security-Policy"]


# ---------------------------------------------------------------- tips (no-JS fallback)

def test_post_tip_with_form(client, csrf):
    response = client.post("/entry/1", data={"author": "V1", "message": "Parry the bite.", "csrf_token": csrf()},
                           follow_redirects=True)
    assert response.status_code == 200
    assert b"Parry the bite." in response.data


def test_empty_tip_shows_errors_and_keeps_input(client, csrf):
    response = client.post("/entry/1", data={"author": "V1", "message": "", "csrf_token": csrf()})
    assert response.status_code == 422
    assert b"Write a tip before sending." in response.data
    assert b'value="V1"' in response.data


def test_tip_is_escaped(client, csrf):
    client.post("/entry/1", data={"author": "x", "message": "<script>alert(1)</script>", "csrf_token": csrf()})
    page = client.get("/entry/1").data
    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_form_without_csrf_is_rejected(client):
    response = client.post("/entry/1", data={"author": "V1", "message": "hi"})
    assert response.status_code == 400


# ---------------------------------------------------------------- admin

def test_add_entry_requires_login(client):
    response = client.get("/entries/new")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_wrong_password(client, csrf):
    response = client.post("/login", data={"username": "admin", "password": "nope", "csrf_token": csrf()})
    assert response.status_code == 401
    assert b"Wrong username or password." in response.data


def test_login_does_not_redirect_to_other_sites(client, csrf):
    response = client.post("/login?next=//evil.example", data={"username": "admin", "password": "test-password",
                                                                "csrf_token": csrf()})
    assert response.headers["Location"] == "/"


def test_admin_creates_entry_with_all_fields(admin, entry_form):
    response = admin.post("/entries/new", data=entry_form(faction="Demons", is_secret="1"), follow_redirects=True)
    page = response.data.decode()
    assert "Test Husk" in page and "Demons // enemy // secret" in page


def test_invalid_entry_keeps_values(admin, entry_form):
    response = admin.post("/entries/new", data=entry_form(lore="", faction="Robots"))
    assert response.status_code == 422
    assert b"Lore is required." in response.data
    assert b"Choose one of the six factions." in response.data
    assert b'value="Test Husk"' in response.data


def test_duplicate_name_rejected(admin, entry_form):
    response = admin.post("/entries/new", data=entry_form(name="filth"))
    assert b"already exists" in response.data


def test_too_long_field_rejected(admin, entry_form):
    response = admin.post("/entries/new", data=entry_form(name="x" * 81))
    assert response.status_code == 422


def test_image_upload(admin, entry_form, app):
    data = entry_form(image=(io.BytesIO(b"fake-png"), "pic.png"))
    admin.post("/entries/new", data=data, content_type="multipart/form-data")
    import os
    assert os.path.exists(os.path.join(app.config["ENEMY_IMAGE_FOLDER"], "test-husk.png"))


def test_image_upload_rejects_other_files(admin, entry_form):
    data = entry_form(image=(io.BytesIO(b"#!/bin/sh"), "evil.sh"))
    response = admin.post("/entries/new", data=data, content_type="multipart/form-data")
    assert response.status_code == 422
    assert b"Image must be" in response.data


def test_admin_edits_entry(admin, entry_form):
    response = admin.post("/entry/1/edit", data=entry_form(name="Filth (edited)"), follow_redirects=True)
    assert b"Filth (edited)" in response.data


def test_admin_deletes_entry_with_form(admin, csrf):
    admin.post("/entry/1/delete", data={"csrf_token": csrf()})
    assert admin.get("/entry/1").status_code == 404


def test_logout(admin, csrf):
    admin.post("/logout", data={"csrf_token": csrf()})
    assert admin.get("/entries/new").status_code == 302
