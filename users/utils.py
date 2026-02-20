from fastapi import HTTPException, Request


def require_authenticated_user(request: Request):
    if not (request.user and request.user.is_authenticated):
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.user


def require_admin(user) -> None:
    if not (user and user.is_admin):
        raise HTTPException(status_code=403, detail="Admin required")
