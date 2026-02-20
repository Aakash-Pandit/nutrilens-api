from fastapi import HTTPException, Request


def require_authenticated_user(request: Request):
    if not request.user or not request.user.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.user


def require_admin(user) -> None:
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin required")
