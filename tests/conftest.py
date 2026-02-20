import os
import sys
import uuid
import warnings
from datetime import datetime

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

import auth.backend as auth_backend
import database.db as db

from application.app import app as fastapi_app
from auth.jwt import create_access_token
from auth.passwords import hash_password
from users.choices import UserType
from users.models import User

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
        username="jane",
        password="secret123",
        email="jane@example.com",
        phone="1234567890",
        gender="female",
        user_type=UserType.REGULAR,
        date_of_birth=None,
    ):
        user = User(
            first_name=first_name.lower(),
            last_name=last_name.lower(),
            username=username.lower(),
            password_hash=hash_password(password),
            email=email,
            phone=phone,
            gender=gender,
            user_type=user_type,
            date_of_birth=date_of_birth or datetime(1990, 1, 1),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user

