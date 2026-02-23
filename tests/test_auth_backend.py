"""Unit tests for auth.backend (JWTAuthBackend, UserPrincipal)."""
import asyncio
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from starlette.requests import Request

from auth.backend import UserPrincipal, JWTAuthBackend
from users.models import User


def test_user_principal_properties():
    p = UserPrincipal(id="id-1", is_admin=True, email="a@b.com")
    assert p.id == "id-1"
    assert p.is_admin is True
    assert p.email == "a@b.com"
    assert p.is_authenticated is True
    assert p.identity == "id-1"


def test_decode_access_token_valid():
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    backend = JWTAuthBackend()
    from jose import jwt
    token = jwt.encode(
        {"sub": "user-uuid-123"},
        os.environ["JWT_SECRET"],
        algorithm=os.environ["JWT_ALGORITHM"],
    )
    payload = backend._decode_access_token(token)
    assert payload["sub"] == "user-uuid-123"


def test_decode_access_token_invalid_raises():
    backend = JWTAuthBackend()
    with pytest.raises(ValueError) as exc_info:
        backend._decode_access_token("invalid-token")
    assert "Invalid token" in str(exc_info.value)


def _run_async(coro):
    return asyncio.run(coro)


def test_authenticate_no_header_returns_unauthenticated():
    backend = JWTAuthBackend()
    conn = MagicMock(spec=Request)
    conn.headers = {}
    result = _run_async(backend.authenticate(conn))
    assert result is not None
    creds, user = result
    assert list(creds.scopes) == []
    assert not user.is_authenticated


def test_authenticate_bearer_invalid_token_returns_unauthenticated():
    backend = JWTAuthBackend()
    conn = MagicMock(spec=Request)
    conn.headers = {"Authorization": "Bearer invalid-token"}
    with patch.object(backend, "verify_google_id_token", return_value=None):
        result = _run_async(backend.authenticate(conn))
    creds, user = result
    assert not user.is_authenticated


def test_authenticate_bearer_valid_jwt_returns_principal():
    backend = JWTAuthBackend()
    user_id = uuid4()
    user = User(
        id=user_id,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        is_admin=False,
    )
    from jose import jwt
    token = jwt.encode(
        {"sub": str(user_id)},
        os.environ.get("JWT_SECRET", "test-secret"),
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
    )
    conn = MagicMock(spec=Request)
    conn.headers = {"Authorization": f"Bearer {token}"}
    with patch.object(backend, "verify_google_id_token", return_value=None):
        with patch("auth.backend.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = user
            mock_session_local.return_value.__enter__.return_value = mock_db
            mock_session_local.return_value.__exit__.return_value = None
            result = _run_async(backend.authenticate(conn))
    assert result is not None
    creds, principal = result
    assert principal.is_authenticated
    assert principal.id == str(user_id)
    assert principal.email == "jane@example.com"
    assert principal.is_admin is False


def test_authenticate_bearer_valid_jwt_user_not_found_returns_unauthenticated():
    backend = JWTAuthBackend()
    user_id = uuid4()
    from jose import jwt
    token = jwt.encode(
        {"sub": str(user_id)},
        os.environ.get("JWT_SECRET", "test-secret"),
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
    )
    conn = MagicMock(spec=Request)
    conn.headers = {"Authorization": f"Bearer {token}"}
    with patch.object(backend, "verify_google_id_token", return_value=None):
        with patch("auth.backend.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session_local.return_value.__enter__.return_value = mock_db
            mock_session_local.return_value.__exit__.return_value = None
            result = _run_async(backend.authenticate(conn))
    creds, user = result
    assert not user.is_authenticated


def test_authenticate_no_bearer_scheme_returns_unauthenticated():
    backend = JWTAuthBackend()
    conn = MagicMock(spec=Request)
    conn.headers = {"Authorization": "Basic xxx"}
    result = _run_async(backend.authenticate(conn))
    creds, user = result
    assert not user.is_authenticated


def test_authenticate_empty_bearer_token_returns_unauthenticated():
    backend = JWTAuthBackend()
    conn = MagicMock(spec=Request)
    conn.headers = {"Authorization": "Bearer "}
    with patch.object(backend, "verify_google_id_token", return_value=None):
        result = _run_async(backend.authenticate(conn))
    creds, user = result
    assert not user.is_authenticated
