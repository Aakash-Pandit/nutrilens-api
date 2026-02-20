import os

import pytest
from jose import jwt


def test_create_and_decode_token():
    """Token created with same secret/algorithm as backend is valid."""
    secret = os.environ.get("JWT_SECRET", "test-secret")
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    token = jwt.encode({"sub": "123"}, secret, algorithm=algorithm)
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    assert payload["sub"] == "123"


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        jwt.decode("not-a-real-token", "test-secret", algorithms=["HS256"])


def test_protected_endpoint_without_token_returns_401(client):
    response = client.get("/users")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_endpoint_with_invalid_token_returns_401(client):
    response = client.get(
        "/users",
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token_succeeds(client, create_user, auth_headers):
    user = create_user(email="auth@example.com", is_admin=True)
    response = client.get("/users", headers=auth_headers(user))
    assert response.status_code == 200
