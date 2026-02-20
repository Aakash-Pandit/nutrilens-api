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
import organizations.db as organizations_db
from application.app import app as fastapi_app
from auth.jwt import create_access_token
from auth.passwords import hash_password
from organizations.models import Organization, Policy, UserOrganization
from users.choices import LeaveType, UserType
from users.models import LeaveRequest, User

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


@pytest.fixture()
def create_organization(db_session):
    def _create_organization(
        *,
        name="Test Organization",
        description="A test organization",
        address="123 Test St",
        email="test@org.com",
        phone="555-0000",
        is_active=True,
    ):
        org = Organization(
            name=name,
            description=description,
            address=address,
            email=email,
            phone=phone,
            is_active=is_active,
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        return org

    return _create_organization


@pytest.fixture()
def create_policy(db_session):
    def _create_policy(
        *,
        organization_id,
        name="Default Policy",
        description="Default leave policy",
        document_name=None,
        file_path=None,
        is_active=True,
    ):
        policy = Policy(
            organization_id=organization_id,
            name=name,
            description=description,
            document_name=document_name,
            file=file_path,
            is_active=is_active,
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        return policy

    return _create_policy


@pytest.fixture()
def create_user_organization(db_session):
    def _create_user_organization(
        *,
        user_id,
        organization_id,
        joined_date=None,
        left_date=None,
        is_active=True,
    ):
        membership = UserOrganization(
            user_id=user_id,
            organization_id=organization_id,
            joined_date=joined_date or datetime(2026, 1, 1).date(),
            left_date=left_date,
            is_active=is_active,
        )
        db_session.add(membership)
        db_session.commit()
        db_session.refresh(membership)
        return membership

    return _create_user_organization


@pytest.fixture()
def create_leave_request(db_session):
    def _create_leave_request(
        *,
        user_id,
        organization_id,
        date=None,
        leave_type=LeaveType.SICK_LEAVE,
        reason=None,
        is_accepted=False,
    ):
        leave_request = LeaveRequest(
            user_id=user_id,
            organization_id=organization_id,
            date=date or datetime(2026, 3, 15).date(),
            leave_type=leave_type,
            reason=reason,
            is_accepted=is_accepted,
        )
        db_session.add(leave_request)
        db_session.commit()
        db_session.refresh(leave_request)
        return leave_request

    return _create_leave_request


@pytest.fixture()
def auth_headers():
    def _auth_headers(user):
        token = create_access_token(
            {"sub": str(user.id), "user_type": str(user.user_type)}
        )
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
