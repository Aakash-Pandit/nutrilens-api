"""Tests for ingredients.tasks (analyze_ingredient_task)."""
import os
from unittest.mock import patch
from uuid import uuid4

import pytest

from ingredients.models import Ingredient
from ingredients.tasks import analyze_ingredient_task
from notifications.choices import NotificationStatus
from notifications.models import Notification
from users.models import User


@pytest.fixture
def sample_user(db_session):
    user = User(
        first_name="Test",
        last_name="User",
        email="taskuser@example.com",
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_ingredient(sample_user, db_session, tmp_path):
    path = tmp_path / "ingredient.jpg"
    path.write_bytes(b"fake image bytes")
    ing = Ingredient(
        file_path=str(path),
        uploaded_by_id=sample_user.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing


def test_analyze_ingredient_task_invalid_id_returns_error():
    result = analyze_ingredient_task("not-a-uuid")
    assert result["ok"] is False
    assert "error" in result
    assert "invalid" in result["error"].lower()


def test_analyze_ingredient_task_nonexistent_ingredient_returns_error(db_session):
    result = analyze_ingredient_task(str(uuid4()))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_analyze_ingredient_task_missing_file_creates_fail_notification(
    sample_ingredient, db_session
):
    ingredient_id = str(sample_ingredient.id)
    recipient_id = sample_ingredient.uploaded_by_id
    os.remove(sample_ingredient.file_path)
    result = analyze_ingredient_task(ingredient_id)
    assert result["ok"] is False
    assert "file not found" in result["error"].lower()
    notifs = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == recipient_id)
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].status == NotificationStatus.FAIL
    assert "ingredient image file not found" in (notifs[0].data or {}).get("error", "")


def test_analyze_ingredient_task_success_creates_notification(
    sample_ingredient, db_session
):
    ingredient_id = str(sample_ingredient.id)
    recipient_id = sample_ingredient.uploaded_by_id
    with patch("ingredients.tasks.detect_text_from_image", return_value="Sugar, Salt"):
        with patch(
            "ingredients.tasks.analyze_ingredients",
            return_value="Sugar: Sweet.\n\nSummary: Ok.\nVerdict: Safe.",
        ):
            with patch("ingredients.tasks.parse_ingredients_to_json") as mock_parse:
                mock_parse.return_value = {
                    "product_metadata": {"summary": "", "verdict": ""},
                    "ingredients": [{"ingredient": "Sugar", "description": "Sweet"}],
                }
                result = analyze_ingredient_task(ingredient_id)
    assert result["ok"] is True
    assert result["ingredient_id"] == ingredient_id
    notifs = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == recipient_id)
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].status == NotificationStatus.SUCCESS
    db_session.expire_all()
    ing = db_session.query(Ingredient).filter(Ingredient.id == sample_ingredient.id).first()
    assert ing is not None
    assert ing.ingredient_details == "Sugar, Salt"
    assert ing.ingredient_analysis is not None


def test_analyze_ingredient_task_ocr_failure_creates_fail_notification(
    sample_ingredient, db_session
):
    ingredient_id = str(sample_ingredient.id)
    recipient_id = sample_ingredient.uploaded_by_id
    with patch(
        "ingredients.tasks.detect_text_from_image",
        side_effect=Exception("OCR failed"),
    ):
        result = analyze_ingredient_task(ingredient_id)
    assert result["ok"] is False
    assert "OCR failed" in result["error"]
    notifs = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == recipient_id)
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].status == NotificationStatus.FAIL
