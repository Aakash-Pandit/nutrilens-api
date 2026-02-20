import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.db import Base
from users.choices import UserType


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    user_type = Column(
        Enum(UserType, name="user_type"), nullable=False, default=UserType.REGULAR
    )
    date_of_birth = Column(Date, nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now())
    modified = Column(DateTime(timezone=True), onupdate=func.now())


class UserRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    gender: str
    user_type: UserType = UserType.REGULAR
    date_of_birth: datetime


class UserItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    gender: str
    user_type: UserType
    date_of_birth: datetime


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    gender: str
    user_type: UserType
    date_of_birth: datetime


class UsersListResponse(BaseModel):
    users: list[UserItem]
    total: int
    message: str

