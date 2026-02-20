from typing import Optional, Tuple

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from starlette.requests import HTTPConnection

from auth.jwt import decode_access_token
from database.db import SessionLocal
from users.models import User


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


class JWTAuthBackend(AuthenticationBackend):
    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[Tuple[AuthCredentials, BaseUser]]:
        auth = conn.headers.get("Authorization")
        if not auth:
            return AuthCredentials([]), UnauthenticatedUser()
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return AuthCredentials([]), UnauthenticatedUser()

        try:
            payload = decode_access_token(token)
        except ValueError:
            return AuthCredentials([]), UnauthenticatedUser()

        user_id = payload.get("sub")
        if not user_id:
            return AuthCredentials([]), UnauthenticatedUser()

        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return AuthCredentials([]), UnauthenticatedUser()

        user_type = getattr(user.user_type, "value", str(user.user_type))
        principal = UserPrincipal(
            user_id=str(user.id),
            user_type=user_type,
            display_name=user.email,
        )
        return AuthCredentials(["authenticated"]), principal
