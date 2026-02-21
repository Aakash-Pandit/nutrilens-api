import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.db import Base


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
    ingredient_analysis = Column(String, nullable=True, default="")
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = relationship("User", backref="ingredients")


class IngredientItem(BaseModel):
    id: str
    file_path: str
    ingredient_details: str | None = None
    ingredient_analysis: str | None = None
    uploaded_by_id: str
    uploaded_at: datetime


class IngredientResponse(BaseModel):
    id: str
    file_path: str
    ingredient_details: str | None = None
    ingredient_analysis: str | None = None
    uploaded_by_id: str
    uploaded_at: datetime


class IngredientsListResponse(BaseModel):
    ingredients: list[IngredientItem]
    total: int
    message: str
