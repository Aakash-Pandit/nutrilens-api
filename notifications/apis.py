from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from application.app import app
from database.db import get_db
from notifications.models import (
    Notification,
    NotificationItem,
    NotificationsListResponse,
    ReadNotificationsPayload,
)
from notifications.choices import NotificationStatus
from users.utils import require_authenticated_user


def _notification_to_item(n: Notification) -> NotificationItem:
    return NotificationItem(
        id=str(n.id),
        recipient_id=str(n.recipient_id),
        read_at=n.read_at,
        data=n.data or {},
        status=n.status,
        created_at=n.created_at,
    )


@app.get("/notifications", response_model=NotificationsListResponse)
async def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    status: NotificationStatus | None = None,
):
    require_authenticated_user(request)
    user_id = UUID(request.user.id)
    query = (
        db.query(Notification)
        .filter(Notification.recipient_id == user_id)
    )
    if status is not None:
        query = query.filter(Notification.status == status)
    rows = query.order_by(Notification.created_at.desc()).all()
    items = [_notification_to_item(r) for r in rows]
    return NotificationsListResponse(
        notifications=items,
        total=len(items),
        message="No notifications found" if not items else "Notifications retrieved",
    )


@app.get("/notifications/{notification_id}", response_model=NotificationItem)
async def get_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    try:
        nid = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification = db.query(Notification).filter(Notification.id == nid).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(notification.recipient_id) != request.user.id:
        raise HTTPException(status_code=403, detail="Not allowed to access this notification")
    return _notification_to_item(notification)


@app.post("/notifications/read")
async def read_notifications(
    payload: ReadNotificationsPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    user_id = UUID(request.user.id)
    ids: list[UUID] = []
    for sid in payload.notification_ids:
        try:
            ids.append(UUID(sid))
        except ValueError:
            continue
    if not ids:
        return {"status": "ok", "message": "No valid notification ids", "updated_count": 0}
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(
            Notification.id.in_(ids),
            Notification.recipient_id == user_id,
        )
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"status": "ok", "message": "Notifications marked as read", "updated_count": updated}
