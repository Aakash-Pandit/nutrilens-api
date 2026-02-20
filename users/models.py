import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    picture_url = Column(String, nullable=True)
    created = Column(DateTime(timezone=True), server_default=func.now())


class UserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    is_admin: bool = False
    picture_url: str | None = None


class UserItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    is_admin: bool
    picture_url: str | None
    created: datetime


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    is_admin: bool
    picture_url: str | None
    created: datetime


class UsersListResponse(BaseModel):
    users: list[UserItem]
    total: int
    message: str
