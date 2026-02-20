from fastapi import HTTPException

from application.app import app


@app.post("/login")
async def login():
    raise HTTPException(
        status_code=400,
        detail="Use Google sign-in. Send Google ID token in Authorization: Bearer <token>.",
    )
