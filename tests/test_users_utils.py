"""Unit tests for users.utils (require_authenticated_user, require_admin)."""
import pytest
from unittest.mock import MagicMock

from users.utils import require_admin, require_authenticated_user


def test_require_authenticated_user_returns_user_when_authenticated():
    request = MagicMock()
    request.user = MagicMock()
    request.user.is_authenticated = True
    request.user.id = "user-123"
    result = require_authenticated_user(request)
    assert result is request.user
    assert result.id == "user-123"


def test_require_authenticated_user_raises_when_no_user():
    request = MagicMock()
    request.user = None
    with pytest.raises(Exception) as exc_info:
        require_authenticated_user(request)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in str(exc_info.value.detail)


def test_require_authenticated_user_raises_when_not_authenticated():
    request = MagicMock()
    request.user = MagicMock()
    request.user.is_authenticated = False
    with pytest.raises(Exception) as exc_info:
        require_authenticated_user(request)
    assert exc_info.value.status_code == 401


def test_require_admin_passes_when_admin():
    user = MagicMock()
    user.is_admin = True
    require_admin(user)


def test_require_admin_raises_when_not_admin():
    user = MagicMock()
    user.is_admin = False
    with pytest.raises(Exception) as exc_info:
        require_admin(user)
    assert exc_info.value.status_code == 403
    assert "Admin required" in str(exc_info.value.detail)


def test_require_admin_raises_when_user_none():
    with pytest.raises(Exception) as exc_info:
        require_admin(None)
    assert exc_info.value.status_code == 403
