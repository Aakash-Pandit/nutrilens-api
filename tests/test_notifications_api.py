"""Tests for notifications API endpoints."""
from uuid import uuid4

import pytest

from notifications.choices import NotificationStatus
from notifications.models import Notification


def test_list_notifications_without_auth_returns_401(client):
    response = client.get("/notifications")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_list_notifications_with_auth_empty(client, create_user, auth_headers):
    user = create_user(email="nobody@example.com")
    response = client.get("/notifications", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert "total" in data
    assert data["notifications"] == []
    assert data["total"] == 0
    assert "message" in data


def test_list_notifications_with_auth_returns_own(
    client, create_user, auth_headers, db_session
):
    user = create_user(email="recipient@example.com")
    n = Notification(
        recipient_id=user.id,
        data={"ingredient_id": str(uuid4())},
        status=NotificationStatus.SUCCESS,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    response = client.get("/notifications", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["id"] == str(n.id)
    assert data["notifications"][0]["recipient_id"] == str(user.id)
    assert data["notifications"][0]["status"] == NotificationStatus.SUCCESS.value
    assert "read_at" in data["notifications"][0]
    assert "created_at" in data["notifications"][0]


def test_list_notifications_filter_by_status(
    client, create_user, auth_headers, db_session
):
    user = create_user(email="filter@example.com")
    n1 = Notification(
        recipient_id=user.id,
        data={},
        status=NotificationStatus.SUCCESS,
    )
    n2 = Notification(
        recipient_id=user.id,
        data={},
        status=NotificationStatus.FAIL,
    )
    db_session.add_all([n1, n2])
    db_session.commit()

    response = client.get(
        "/notifications",
        headers=auth_headers(user),
        params={"status": NotificationStatus.SUCCESS.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["status"] == NotificationStatus.SUCCESS.value


def test_list_notifications_excludes_other_users(
    client, create_user, auth_headers, db_session
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    n = Notification(
        recipient_id=owner.id,
        data={},
        status=NotificationStatus.SUCCESS,
    )
    db_session.add(n)
    db_session.commit()

    response = client.get("/notifications", headers=auth_headers(other))
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["notifications"] == []


def test_get_notification_with_auth_own(
    client, create_user, auth_headers, db_session
):
    user = create_user(email="getter@example.com")
    n = Notification(
        recipient_id=user.id,
        data={"key": "value"},
        status=NotificationStatus.SUCCESS,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    response = client.get(
        f"/notifications/{n.id}",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(n.id)
    assert data["recipient_id"] == str(user.id)
    assert data["data"] == {"key": "value"}
    assert data["status"] == NotificationStatus.SUCCESS.value


def test_get_notification_other_user_returns_403(
    client, create_user, auth_headers, db_session
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    n = Notification(
        recipient_id=owner.id,
        data={},
        status=NotificationStatus.SUCCESS,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    response = client.get(
        f"/notifications/{n.id}",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    assert "detail" in response.json()


def test_get_notification_not_found_returns_404(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.get(
        "/notifications/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_get_notification_invalid_uuid_returns_404(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.get(
        "/notifications/not-a-uuid",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_read_notifications_without_auth_returns_401(client):
    response = client.post(
        "/notifications/read",
        json={"notification_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 401


def test_read_notifications_empty_ids(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["updated_count"] == 0


def test_read_notifications_valid_ids(
    client, create_user, auth_headers, db_session
):
    user = create_user(email="reader@example.com")
    n = Notification(
        recipient_id=user.id,
        data={},
        status=NotificationStatus.SUCCESS,
        read_at=None,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": [str(n.id)]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["updated_count"] == 1
    assert "message" in data

    db_session.refresh(n)
    assert n.read_at is not None


def test_read_notifications_ignores_other_users(
    client, create_user, auth_headers, db_session
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    n = Notification(
        recipient_id=owner.id,
        data={},
        status=NotificationStatus.SUCCESS,
        read_at=None,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    response = client.post(
        "/notifications/read",
        headers=auth_headers(other),
        json={"notification_ids": [str(n.id)]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 0

    db_session.refresh(n)
    assert n.read_at is None


def test_read_notifications_invalid_ids_skipped(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": ["not-a-uuid", "00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["updated_count"] == 0


def test_stream_notifications_without_auth_returns_401(client, create_user):
    user = create_user(email="user@example.com")
    response = client.get(
        f"/notifications/stream/{user.id}",
    )
    assert response.status_code == 401


def test_stream_notifications_other_user_returns_403(
    client, create_user, auth_headers
):
    user = create_user(email="user@example.com")
    other = create_user(email="other@example.com")
    response = client.get(
        f"/notifications/stream/{user.id}",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    assert "detail" in response.json()
