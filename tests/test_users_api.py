import pytest
from fastapi import HTTPException

from users.utils import coerce_user_type, require_admin
from users.choices import UserType


def test_create_user_public(client):
    response = client.post(
        "/users",
        json={
            "first_name": "Sam",
            "last_name": "Hill",
            "username": "sammy",
            "password": "secret123",
            "email": "sam@example.com",
            "phone": "5555551111",
            "gender": "male",
            "user_type": "REGULAR",
            "date_of_birth": "1991-02-03T00:00:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["first_name"] == "sam"
    assert payload["last_name"] == "hill"
    assert payload["username"] == "sammy"


def test_get_users_requires_admin(client, create_user, auth_headers):
    admin = create_user(
        username="admin",
        email="admin@example.com",
        user_type=UserType.ADMIN,
    )
    create_user(username="staff", email="staff@example.com")

    response = client.get("/users", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["total"] == 2

    regular = create_user(username="regular", email="regular@example.com")
    response = client.get("/users", headers=auth_headers(regular))
    assert response.status_code == 403


def test_get_user_requires_same_user(client, create_user, auth_headers):
    user = create_user(username="owner", email="owner@example.com")
    other = create_user(username="other", email="other@example.com")

    response = client.get(f"/users/{user.id}", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)

    response = client.get(f"/users/{user.id}", headers=auth_headers(other))
    assert response.status_code == 403


def test_delete_user(client, create_user, auth_headers):
    admin = create_user(
        username="admin",
        email="admin@example.com",
        user_type=UserType.ADMIN,
    )
    user = create_user(username="delete", email="delete@example.com")

    response = client.delete(f"/users/{user.id}", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted"


def test_user_type_helpers():
    assert coerce_user_type("admin") == UserType.ADMIN
    require_admin("ADMIN")
    with pytest.raises(HTTPException):
        require_admin("REGULAR")
    with pytest.raises(HTTPException):
        coerce_user_type("visitor")


def test_create_user_duplicate_username_returns_409(client, create_user):
    create_user(username="existing", email="first@example.com")
    response = client.post(
        "/users",
        json={
            "first_name": "Other",
            "last_name": "User",
            "username": "existing",
            "password": "secret123",
            "email": "second@example.com",
            "phone": "5555552222",
            "gender": "male",
            "user_type": "REGULAR",
            "date_of_birth": "1992-01-01T00:00:00",
        },
    )
    assert response.status_code == 409
    assert "username" in response.json()["detail"].lower()


def test_create_user_duplicate_email_returns_409(client, create_user):
    create_user(username="user1", email="same@example.com")
    response = client.post(
        "/users",
        json={
            "first_name": "Other",
            "last_name": "User",
            "username": "user2",
            "password": "secret123",
            "email": "same@example.com",
            "phone": "5555553333",
            "gender": "female",
            "user_type": "REGULAR",
            "date_of_birth": "1993-01-01T00:00:00",
        },
    )
    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()


def test_delete_user_not_found_returns_404(client, create_user, auth_headers):
    admin = create_user(
        username="admin",
        email="admin@example.com",
        user_type=UserType.ADMIN,
    )
    response = client.delete(
        "/users/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
