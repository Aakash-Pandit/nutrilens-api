from datetime import timedelta

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from application.app import app
from auth.jwt import JWT_EXPIRE_MINUTES, create_access_token
from auth.passwords import verify_password
from database.db import get_db
from users.models import User


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@app.post("/login", response_model=TokenResponse)
async def login(payload: TokenRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {"sub": str(user.id), "user_type": str(user.user_type)},
        expires_delta=timedelta(minutes=JWT_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token, token_type="bearer")
