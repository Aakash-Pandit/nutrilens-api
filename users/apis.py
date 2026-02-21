from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID

from application.app import app
from database.db import drop_users_table, get_db
from users.models import (
    User,
    UserItem,
    UsersListResponse,
)
from users.utils import require_admin, require_authenticated_user


@app.get("/users", response_model=UsersListResponse)
async def get_users(request: Request, db: Session = Depends(get_db)):

    require_admin(request.user)

    rows = db.query(User).order_by(User.created.desc()).all()
    users = [
        UserItem(
            id=str(row.id),
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            is_admin=row.is_admin,
            picture_url=row.picture_url,
            created=row.created,
        )
        for row in rows
    ]
    return UsersListResponse(
        users=users,
        total=len(users),
        message="No users found" if not users else "Users retrieved",
    )


@app.get("/users/{user_id}", response_model=UserItem)
async def get_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    if (request.user.id != user_id) and (not request.user.is_admin):
        raise HTTPException(status_code=403, detail="User access restricted")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserItem(
        id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        is_admin=user.is_admin,
        picture_url=user.picture_url,
        created=user.created,
    )


@app.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "ok", "message": "User deleted"}


@app.delete("/admin/drop-users-db")
async def drop_users_db_table():
    drop_users_table()
    return {"status": "ok", "message": "Users database table dropped"}
