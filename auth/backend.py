import os
from typing import Any, Optional, Tuple
from uuid import UUID

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from starlette.requests import HTTPConnection

from database.db import SessionLocal
from users.models import User

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


class UserPrincipal(BaseUser):
    def __init__(self, user_id: str, is_admin: bool, display_name: str) -> None:
        self.user_id = user_id
        self.is_admin = is_admin
        self.user_type = "ADMIN" if is_admin else "REGULAR"
        self._display_name = display_name

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def identity(self) -> str:
        return self.user_id


def _get_or_create_user_from_google(payload: dict) -> User | None:
    email = (payload.get("email") or "").strip()
    if not email:
        return None
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user
        given = (payload.get("given_name") or "").strip() or "User"
        family = (payload.get("family_name") or "").strip()
        picture = (payload.get("picture") or "").strip() or None
        new_user = User(
            first_name=given,
            last_name=family,
            email=email,
            is_admin=False,
            picture_url=picture,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user


class JWTAuthBackend(AuthenticationBackend):
    def verify_google_id_token(self, token: str) -> dict[str, Any] | None:
        if not GOOGLE_CLIENT_ID:
            return None
        try:
            request = google_requests.Request()
            return id_token.verify_oauth2_token(token, request, GOOGLE_CLIENT_ID)
        except (ValueError, Exception):
            return None

    def _decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            raise ValueError("Invalid token") from exc

    def _principal_from_user(self, user: User) -> Tuple[AuthCredentials, UserPrincipal]:
        principal = UserPrincipal(
            user_id=str(user.id),
            is_admin=user.is_admin,
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

        google_payload = self.verify_google_id_token(token)
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
