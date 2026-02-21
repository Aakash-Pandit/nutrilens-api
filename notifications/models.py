import enum
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.db import Base
from users.models import User  # noqa: F401 - needed so relationship("User") resolves
from notifications.choices import NotificationStatus


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    data = Column(JSON, nullable=False, default=dict)
    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.SUCCESS,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", backref="notifications")


class NotificationItem(BaseModel):
    id: str
    recipient_id: str
    read_at: datetime | None
    data: dict
    status: NotificationStatus
    created_at: datetime


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationItem]
    total: int
    message: str


class ReadNotificationsPayload(BaseModel):
    notification_ids: list[str]
