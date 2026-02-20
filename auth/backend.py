from datetime import date
import os
from typing import Any, Optional, Tuple
from uuid import UUID

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from jose import JWTError, jwt

from sqlalchemy.exc import IntegrityError

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from starlette.requests import HTTPConnection

from database.db import SessionLocal

from users.choices import UserType
from users.models import User



JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


class UserPrincipal(BaseUser):
    def __init__(self, user_id: str, user_type: str, display_name: str) -> None:
        self.user_id = user_id
        self.user_type = user_type
        self._display_name = display_name

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def identity(self) -> str:
        return self.user_id


def _get_or_create_user_from_google(payload: dict) -> User | None:
    """Look up user by email; if not found, create and return. Returns None on failure."""
    email = (payload.get("email") or "").strip()
    if not email:
        return None

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user

        given = (payload.get("given_name") or "").strip() or "User"
        family = (payload.get("family_name") or "").strip()
        local_part = email.split("@")[0] if "@" in email else "user"
        sub = payload.get("sub") or ""
        username_base = f"{local_part}_{sub[-6:]}" if sub else local_part
        username = username_base
        attempt = 0
        while True:
            try:
                new_user = User(
                    first_name=given,
                    last_name=family,
                    username=username,
                    email=email,
                    gender="other",
                    user_type=UserType.REGULAR,
                    date_of_birth=date(2000, 1, 1),
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                return new_user
            except IntegrityError:
                db.rollback()
                attempt += 1
                username = f"{username_base}{attempt}"
                if attempt > 100:
                    return None


class JWTAuthBackend(AuthenticationBackend):
    async def verify_google_id_token(self, token: str) -> dict[str, Any] | None:
        if not GOOGLE_CLIENT_ID:
            return None
        try:
            request = google_requests.Request()
            payload = id_token.verify_oauth2_token(
                token, request, GOOGLE_CLIENT_ID
            )
            return payload
        except (ValueError, Exception):
            return None

    def _decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            raise ValueError("Invalid token") from exc

    def _principal_from_user(self, user: User) -> Tuple[AuthCredentials, UserPrincipal]:
        user_type = getattr(user.user_type, "value", str(user.user_type))
        principal = UserPrincipal(
            user_id=str(user.id),
            user_type=user_type,
            display_name=user.email,
        )
        return AuthCredentials(["authenticated"]), principal

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[Tuple[AuthCredentials, BaseUser]]:
        auth = conn.headers.get("Authorization")
        if not auth:
            return AuthCredentials([]), UnauthenticatedUser()
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return AuthCredentials([]), UnauthenticatedUser()

        google_payload = await self.verify_google_id_token(token)
        if google_payload:
            user = _get_or_create_user_from_google(google_payload)
            if user:
                return self._principal_from_user(user)

        try:
            payload = self._decode_access_token(token)
        except ValueError:
            return AuthCredentials([]), UnauthenticatedUser()

        user_id = payload.get("sub")
        if not user_id:
            return AuthCredentials([]), UnauthenticatedUser()

        try:
            user_uuid = UUID(user_id)
        except (ValueError, TypeError):
            return AuthCredentials([]), UnauthenticatedUser()

        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_uuid).first()

        if not user:
            return AuthCredentials([]), UnauthenticatedUser()

        return self._principal_from_user(user)
