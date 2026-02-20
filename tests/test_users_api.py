def test_get_users_without_auth_returns_401(client):
    response = client.get("/users")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_users_requires_admin(client, create_user, auth_headers):
    admin = create_user(email="admin@example.com", is_admin=True)
    create_user(email="staff@example.com")
    response = client.get("/users", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["total"] == 2

    regular = create_user(email="regular@example.com")
    response = client.get("/users", headers=auth_headers(regular))
    assert response.status_code == 403


def test_get_user_requires_same_user(client, create_user, auth_headers):
    user = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    response = client.get(f"/users/{user.id}", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    response = client.get(f"/users/{user.id}", headers=auth_headers(other))
    assert response.status_code == 403


def test_get_user_not_found_returns_404(client, create_user, auth_headers):
    # 404 only when requester is allowed to see that user (self or admin) but user doesn't exist
    admin = create_user(email="admin@example.com", is_admin=True)
    response = client.get(
        "/users/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user(client, create_user, auth_headers):
    admin = create_user(email="admin@example.com", is_admin=True)
    user = create_user(email="delete@example.com")
    response = client.delete(f"/users/{user.id}", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted"


def test_delete_user_without_auth_returns_401(client, create_user):
    user = create_user(email="delete@example.com")
    response = client.delete(f"/users/{user.id}")
    assert response.status_code == 401


def test_delete_user_not_found_returns_404(client, create_user, auth_headers):
    admin = create_user(email="admin@example.com", is_admin=True)
    response = client.delete(
        "/users/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
