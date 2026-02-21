import json
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.db import Base
from users.models import User  # noqa: F401 - needed so relationship("User") resolves


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False)
    ingredient_details = Column(String, nullable=True, default="")
    ingredient_analysis = Column(JSON, nullable=True, default=dict())
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = relationship("User", backref="ingredients")


def _coerce_analysis_to_dict(v):
    """Accept dict or JSON string (e.g. from DB) for ingredient_analysis."""
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return {"raw": v}
    return None


class IngredientItem(BaseModel):
    id: str
    file_path: str
    ingredient_details: str | None = None
    ingredient_analysis: dict | None = None
    uploaded_by_id: str
    uploaded_at: datetime

    @field_validator("ingredient_analysis", mode="before")
    @classmethod
    def normalize_ingredient_analysis(cls, v):
        return _coerce_analysis_to_dict(v)


class IngredientResponse(BaseModel):
    id: str
    file_path: str
    ingredient_details: str | None = None
    ingredient_analysis: dict | None = None
    uploaded_by_id: str
    uploaded_at: datetime

    @field_validator("ingredient_analysis", mode="before")
    @classmethod
    def normalize_ingredient_analysis(cls, v):
        return _coerce_analysis_to_dict(v)


class IngredientsListResponse(BaseModel):
    ingredients: list[IngredientItem]
    total: int
    message: str
