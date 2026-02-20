import os
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID

from application.app import app
from database.db import get_db, drop_ingredients_table
from ingredients.models import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    Ingredient,
    IngredientItem,
    IngredientsListResponse,
)
from users.utils import require_authenticated_user, require_admin

UPLOAD_DIR = Path(os.getenv("INGREDIENTS_UPLOAD_DIR", "uploads/ingredients"))


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(file: UploadFile) -> str:
    _ensure_upload_dir()
    ext = Path(file.filename or "image").suffix or ".jpg"
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"
    name = f"{uuid.uuid4()}{ext}"
    path = UPLOAD_DIR / name
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(path)


@app.post("/ingredients", response_model=IngredientItem)
async def create_ingredient(
    request: Request,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, GIF, WebP)"),
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Image only. Allowed: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}",
        )
    file_path = _save_upload(file)
    user_id = UUID(request.user.user_id)
    ingredient = Ingredient(
        file_path=file_path,
        uploaded_by_id=user_id,
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return IngredientItem(
        id=str(ingredient.id),
        file_path=ingredient.file_path,
        uploaded_by_id=str(ingredient.uploaded_by_id),
        uploaded_at=ingredient.uploaded_at,
    )


@app.get("/ingredients", response_model=IngredientsListResponse)
async def list_ingredients(
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    rows = db.query(Ingredient).order_by(Ingredient.uploaded_at.desc()).all()
    items = [
        IngredientItem(
            id=str(r.id),
            file_path=r.file_path,
            uploaded_by_id=str(r.uploaded_by_id),
            uploaded_at=r.uploaded_at,
        )
        for r in rows
    ]
    return IngredientsListResponse(
        ingredients=items,
        total=len(items),
        message="No ingredients found" if not items else "Ingredients retrieved",
    )


@app.get("/ingredients/{ingredient_id}", response_model=IngredientItem)
async def get_ingredient(
    ingredient_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ingredient = db.query(Ingredient).filter(Ingredient.id == uid).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return IngredientItem(
        id=str(ingredient.id),
        file_path=ingredient.file_path,
        uploaded_by_id=str(ingredient.uploaded_by_id),
        uploaded_at=ingredient.uploaded_at,
    )


@app.delete("/ingredients/{ingredient_id}")
async def delete_ingredient(
    ingredient_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_authenticated_user(request)
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ingredient = db.query(Ingredient).filter(Ingredient.id == uid).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if request.user.user_id != str(ingredient.uploaded_by_id) and not request.user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete another user's ingredient")
    if os.path.isfile(ingredient.file_path):
        try:
            os.remove(ingredient.file_path)
        except OSError:
            pass
    db.delete(ingredient)
    db.commit()
    return {"status": "ok", "message": "Ingredient deleted"}


@app.delete("/admin/drop-ingredients-db")
async def drop_ingredients_db_table(request: Request):
    require_admin(request.user)
    drop_ingredients_table()
    return {"status": "ok", "message": "Ingredients database table dropped"}
