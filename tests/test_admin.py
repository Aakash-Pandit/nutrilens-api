"""Tests for admin endpoints (drop-db, drop-users-db)."""


def test_drop_database_without_auth_returns_401(client):
    response = client.delete("/admin/drop-db")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_drop_database_with_auth_returns_200(client, create_user, auth_headers):
    user = create_user(email="admin@example.com")
    response = client.delete(
        "/admin/drop-db",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data


def test_drop_users_db_without_auth_returns_401(client):
    response = client.delete("/admin/drop-users-db")
    assert response.status_code == 401


def test_drop_users_db_with_auth_returns_200(client, create_user, auth_headers):
    user = create_user(email="admin@example.com")
    response = client.delete(
        "/admin/drop-users-db",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data
