import os
import sys
import uuid
import warnings
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
# Use a test-only upload dir so ingredient uploads don't touch project
_test_uploads = Path(PROJECT_ROOT) / "tests" / ".test_ingredients_uploads"
os.environ.setdefault("INGREDIENTS_UPLOAD_DIR", str(_test_uploads))

import auth.backend as auth_backend
import database.db as db
from jose import jwt

from application.app import app as fastapi_app
from notifications.choices import NotificationStatus
from notifications.models import Notification
from users.models import User

# Test-only JWT helper: same format as backend expects (payload["sub"] = user id)
def create_access_token(payload: dict) -> str:
    secret = os.environ.get("JWT_SECRET", "test-secret")
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    return jwt.encode(payload, secret, algorithm=algorithm)

_original_uuid_bind_processor = UUID.bind_processor


def _uuid_bind_processor(self, dialect):
    processor = _original_uuid_bind_processor(self, dialect)
    if dialect.name != "sqlite":
        return processor

    def process(value):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(str(value)).hex

    return process


UUID.bind_processor = _uuid_bind_processor


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


@pytest.fixture(scope="session")
def db_engine(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@pytest.fixture()
def app(db_engine):
    db.engine = db_engine
    db.SessionLocal.configure(bind=db_engine)
    return fastapi_app


@pytest.fixture(autouse=True)
def clean_db(app, db_engine):
    db.Base.metadata.drop_all(bind=db_engine)
    db.Base.metadata.create_all(bind=db_engine)
    yield


@pytest.fixture()
def client(app):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The 'app' shortcut is now deprecated",
            category=DeprecationWarning,
        )
        with TestClient(app) as client:
            yield client


@pytest.fixture()
def db_session():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def create_user(db_session):
    def _create_user(
        *,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        is_admin=False,
        picture_url=None,
    ):
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_admin=is_admin,
            picture_url=picture_url,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture()
def auth_headers():
    def _headers(user):
        token = create_access_token({"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def create_notification(db_session, create_user):
    def _create_notification(
        *,
        recipient=None,
        status=NotificationStatus.SUCCESS,
        data=None,
        read_at=None,
    ):
        if recipient is None:
            recipient = create_user(email="recipient@example.com")
        notif = Notification(
            recipient_id=recipient.id,
            status=status,
            data=data or {"ingredient_id": "test-123"},
            read_at=read_at,
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)
        return notif

    return _create_notification

