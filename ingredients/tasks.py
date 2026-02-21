import logging
import os
from uuid import UUID

from celery_app import celery_app
from sqlalchemy.orm import Session

from ai.image_processing import detect_text_from_image
from ai.ingredients_analysis import analyze_ingredients
from database.db import SessionLocal
from ingredients.models import Ingredient
from ingredients.utils import parse_ingredients_to_json

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="ingredients.analyze_ingredient")
def analyze_ingredient_task(self, ingredient_id: str) -> dict:
    """
    Run OCR on the ingredient image and AI analysis, then save to DB.
    Called asynchronously by the API.
    """
    logger.info("Starting analyze_ingredient task for ingredient_id=%s", ingredient_id)
    try:
        uid = UUID(ingredient_id)
    except (ValueError, TypeError):
        logger.warning("Invalid ingredient_id: %s", ingredient_id)
        return {"ok": False, "error": "invalid ingredient id"}
    db: Session = SessionLocal()
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == uid).first()
        if not ingredient:
            logger.warning("Ingredient not found: %s", ingredient_id)
            return {"ok": False, "error": "ingredient not found"}
        if not ingredient.file_path or not os.path.isfile(ingredient.file_path):
            logger.warning("Ingredient image file not found: ingredient_id=%s path=%s", ingredient_id, ingredient.file_path)
            return {"ok": False, "error": "ingredient image file not found"}
        details_text = ""
        try:
            details_text = detect_text_from_image(ingredient.file_path)
            logger.info("OCR completed for ingredient_id=%s, extracted %d chars", ingredient_id, len(details_text or ""))
        except Exception as e:
            logger.exception("OCR failed for ingredient_id=%s: %s", ingredient_id, e)
            details_text = ""
        ingredient.ingredient_details = details_text or None
        analysis_text = ""
        try:
            analysis_text = analyze_ingredients(details_text)
            logger.info("Analysis completed for ingredient_id=%s, response %d chars", ingredient_id, len(analysis_text or ""))
            analysis_dict = parse_ingredients_to_json(analysis_text)
            ingredient.ingredient_analysis = analysis_dict if isinstance(analysis_dict, dict) else None
        except Exception as e:
            logger.exception("Analysis failed for ingredient_id=%s: %s", ingredient_id, e)
            ingredient.ingredient_analysis = None
        db.commit()
        logger.info("Analyze_ingredient task finished successfully for ingredient_id=%s", ingredient_id)
        return {"ok": True, "ingredient_id": ingredient_id}
    finally:
        db.close()
