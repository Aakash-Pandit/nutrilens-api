from fastapi import HTTPException, Request

PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/create_token",
}


def require_authenticated_user(request: Request):
    if request.url.path in PUBLIC_PATHS:
        return None
    if request.url.path == "/users" and request.method.upper() == "POST":
        return None
    if request.url.path == "/login" and request.method.upper() == "POST":
        return None
    if not request.user or not request.user.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.user
