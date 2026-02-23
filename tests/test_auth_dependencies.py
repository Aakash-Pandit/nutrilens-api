"""Unit tests for auth.dependencies (require_authenticated_user, PUBLIC_PATHS)."""
from unittest.mock import MagicMock

import pytest

from auth.dependencies import require_authenticated_user, PUBLIC_PATHS


def test_public_paths_include_root_and_health():
    assert "/" in PUBLIC_PATHS
    assert "/health" in PUBLIC_PATHS
    assert "/docs" in PUBLIC_PATHS
    assert "/openapi.json" in PUBLIC_PATHS


def test_require_authenticated_user_public_path_returns_none():
    for path in ["/", "/health", "/docs", "/openapi.json", "/auth/create_token"]:
        request = MagicMock()
        request.url = MagicMock()
        request.url.path = path
        request.user = MagicMock()
        request.user.is_authenticated = False
        result = require_authenticated_user(request)
        assert result is None


def test_require_authenticated_user_protected_path_unauthenticated_raises():
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/users"
    request.user = MagicMock()
    request.user.is_authenticated = False
    with pytest.raises(Exception) as exc_info:
        require_authenticated_user(request)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in str(exc_info.value.detail)


def test_require_authenticated_user_protected_path_no_user_raises():
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/ingredients"
    request.user = None
    with pytest.raises(Exception) as exc_info:
        require_authenticated_user(request)
    assert exc_info.value.status_code == 401


def test_require_authenticated_user_protected_path_authenticated_returns_user():
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/ingredients"
    request.user = MagicMock()
    request.user.is_authenticated = True
    result = require_authenticated_user(request)
    assert result is request.user
