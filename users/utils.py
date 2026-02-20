from users.choices import UserType
from fastapi import HTTPException, Request


def require_admin(user_type: UserType):
    if user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


def require_authenticated_user(request: Request):
    """Raise 401 if user is not authenticated."""
    if not request.user or not request.user.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.user
