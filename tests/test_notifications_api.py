"""Tests for notifications API: list, get one, read (bulk)."""

import pytest

from notifications.choices import NotificationStatus


def test_list_notifications_without_auth_returns_401(client):
    response = client.get("/notifications")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_list_notifications_with_auth_empty(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.get("/notifications", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data["notifications"] == []
    assert data["total"] == 0
    assert "message" in data


def test_list_notifications_with_auth_returns_own(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="owner@example.com")
    create_notification(recipient=user, status=NotificationStatus.SUCCESS)
    create_notification(recipient=user, status=NotificationStatus.FAIL)
    response = client.get("/notifications", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert len(data["notifications"]) == 2
    assert data["total"] == 2
    ids = {n["id"] for n in data["notifications"]}
    assert len(ids) == 2
    for n in data["notifications"]:
        assert n["recipient_id"] == str(user.id)
        assert n["status"] in ("success", "fail")
        assert "data" in n
        assert "created_at" in n


def test_list_notifications_filters_by_status_success(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="user@example.com")
    create_notification(recipient=user, status=NotificationStatus.SUCCESS)
    create_notification(recipient=user, status=NotificationStatus.FAIL)
    response = client.get(
        "/notifications?status=success",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["status"] == "success"


def test_list_notifications_filters_by_status_fail(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="user@example.com")
    create_notification(recipient=user, status=NotificationStatus.FAIL)
    create_notification(recipient=user, status=NotificationStatus.SUCCESS)
    response = client.get(
        "/notifications?status=fail",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["status"] == "fail"


def test_list_notifications_excludes_other_users(
    client, create_user, auth_headers, create_notification
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    create_notification(recipient=owner)
    create_notification(recipient=other)
    response = client.get("/notifications", headers=auth_headers(owner))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["recipient_id"] == str(owner.id)


def test_get_notification_without_auth_returns_401(
    client, create_user, create_notification
):
    user = create_user(email="user@example.com")
    notif = create_notification(recipient=user)
    response = client.get(f"/notifications/{notif.id}")
    assert response.status_code == 401


def test_get_notification_with_auth_owner(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="owner@example.com")
    notif = create_notification(
        recipient=user,
        status=NotificationStatus.FAIL,
        data={"ingredient_id": "abc", "error": "OCR failed"},
    )
    response = client.get(
        f"/notifications/{notif.id}",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(notif.id)
    assert data["recipient_id"] == str(user.id)
    assert data["status"] == "fail"
    assert data["data"]["ingredient_id"] == "abc"
    assert data["data"]["error"] == "OCR failed"
    assert "created_at" in data


def test_get_notification_other_user_returns_403(
    client, create_user, auth_headers, create_notification
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    notif = create_notification(recipient=owner)
    response = client.get(
        f"/notifications/{notif.id}",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to access this notification"


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


def test_read_notifications_without_auth_returns_401(
    client, create_user, create_notification
):
    user = create_user(email="user@example.com")
    notif = create_notification(recipient=user)
    response = client.post(
        "/notifications/read",
        json={"notification_ids": [str(notif.id)]},
    )
    assert response.status_code == 401


def test_read_notifications_with_auth_updates_own(
    client, create_user, auth_headers, create_notification, db_session
):
    from notifications.models import Notification

    user = create_user(email="user@example.com")
    notif = create_notification(recipient=user, read_at=None)
    nid = notif.id
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": [str(nid)]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["updated_count"] == 1
    # API used a different session; expire so we read committed state from DB
    db_session.expire_all()
    updated = db_session.query(Notification).filter(Notification.id == nid).first()
    assert updated is not None
    assert updated.read_at is not None


def test_read_notifications_empty_list(
    client, create_user, auth_headers
):
    user = create_user(email="user@example.com")
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 0
    assert "No valid" in data["message"] or "ok" in data["status"]


def test_read_notifications_invalid_ids_ignored(
    client, create_user, auth_headers
):
    user = create_user(email="user@example.com")
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={"notification_ids": ["not-a-uuid", "123"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 0


def test_read_notifications_other_users_not_updated(
    client, create_user, auth_headers, create_notification
):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    notif_owner = create_notification(recipient=owner)
    notif_other = create_notification(recipient=other)
    # Other user tries to mark owner's notification as read
    response = client.post(
        "/notifications/read",
        headers=auth_headers(other),
        json={"notification_ids": [str(notif_owner.id), str(notif_other.id)]},
    )
    assert response.status_code == 200
    # Only other's notification should be updated
    assert response.json()["updated_count"] == 1


def test_notification_item_includes_read_at_null_when_unread(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="user@example.com")
    create_notification(recipient=user, read_at=None)
    response = client.get("/notifications", headers=auth_headers(user))
    assert response.status_code == 200
    assert len(response.json()["notifications"]) == 1
    assert response.json()["notifications"][0]["read_at"] is None


def test_read_notifications_mixed_valid_invalid(
    client, create_user, auth_headers, create_notification
):
    user = create_user(email="user@example.com")
    notif1 = create_notification(recipient=user)
    notif2 = create_notification(recipient=user)
    response = client.post(
        "/notifications/read",
        headers=auth_headers(user),
        json={
            "notification_ids": [
                str(notif1.id),
                "invalid",
                str(notif2.id),
                "00000000-0000-0000-0000-000000000000",
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 2
