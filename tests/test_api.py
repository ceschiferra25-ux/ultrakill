"""JSON API: every HTTP method, permissions, validation and CSRF."""


def headers(token):
    return {"X-CSRF-Token": token}


def test_list_entries(client):
    data = client.get("/api/entries").get_json()
    assert data["count"] == 41 == len(data["entries"])


def test_list_entries_with_filters(client):
    data = client.get("/api/entries?faction=Prime Souls&category=boss").get_json()
    assert {e["name"] for e in data["entries"]} == {"Minos Prime", "Sisyphus Prime"}


def test_secret_filter(client):
    data = client.get("/api/entries?secret=1").get_json()
    assert all(e["is_secret"] for e in data["entries"])


def test_get_one_entry(client):
    entry = client.get("/api/entries/1").get_json()
    assert entry["name"] == "Filth"
    assert entry["faction_icon"].endswith("husks.svg")


def test_get_missing_entry(client):
    response = client.get("/api/entries/9999")
    assert response.status_code == 404
    assert response.get_json()["error"]


def test_post_comment(client, csrf):
    response = client.post("/api/entries/1/comments", json={"author": "V1", "message": "Slide."}, headers=headers(csrf()))
    assert response.status_code == 201
    assert client.get("/api/entries/1/comments").get_json()[0]["message"] == "Slide."


def test_post_comment_validation(client, csrf):
    response = client.post("/api/entries/1/comments", json={"author": "", "message": "x" * 1001},
                           headers=headers(csrf()))
    assert response.status_code == 422
    assert set(response.get_json()["fields"]) == {"author", "message"}


def test_post_comment_without_csrf(client):
    response = client.post("/api/entries/1/comments", json={"author": "V1", "message": "hi"})
    assert response.status_code == 400


def test_delete_comment_needs_admin(client, csrf):
    client.post("/api/entries/1/comments", json={"author": "V1", "message": "hi"}, headers=headers(csrf()))
    assert client.delete("/api/comments/1", headers=headers(csrf())).status_code == 401


def test_admin_deletes_comment(admin, csrf):
    admin.post("/api/entries/1/comments", json={"author": "V1", "message": "hi"}, headers=headers(csrf()))
    assert admin.delete("/api/comments/1", headers=headers(csrf())).status_code == 204
    assert admin.delete("/api/comments/1", headers=headers(csrf())).status_code == 404


def test_put_entry_needs_admin(client, csrf):
    assert client.put("/api/entries/1", json={}, headers=headers(csrf())).status_code == 401


def test_admin_puts_entry(admin, csrf):
    entry = admin.get("/api/entries/1").get_json()
    entry["lore"] = "Updated through the API."
    response = admin.put("/api/entries/1", json=entry, headers=headers(csrf()))
    assert response.status_code == 200
    assert response.get_json()["lore"] == "Updated through the API."


def test_admin_put_invalid_entry(admin, csrf):
    response = admin.put("/api/entries/1", json={"name": ""}, headers=headers(csrf()))
    assert response.status_code == 422
    assert "name" in response.get_json()["fields"]


def test_admin_deletes_entry_and_its_comments(admin, csrf):
    admin.post("/api/entries/2/comments", json={"author": "V1", "message": "hi"}, headers=headers(csrf()))
    assert admin.delete("/api/entries/2", headers=headers(csrf())).status_code == 204
    assert admin.get("/api/entries/2").status_code == 404
    assert admin.get("/api/entries/2/comments").status_code == 404


def test_method_not_allowed_is_json(client):
    response = client.patch("/api/entries")
    assert response.status_code in (400, 405)  # CSRF check runs first for unsafe methods
    assert response.is_json
