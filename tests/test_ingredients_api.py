import io

import pytest
from PIL import Image

from ingredients.models import Ingredient


def _make_jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buf, "JPEG")
    return buf.getvalue()


def test_list_ingredients_without_auth_returns_401(client):
    response = client.get("/ingredients")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_create_ingredient_without_auth_returns_401(client):
    response = client.post(
        "/ingredients",
        files={"file": ("image.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_create_ingredient_with_auth_succeeds(client, create_user, auth_headers):
    user = create_user(email="uploader@example.com")
    response = client.post(
        "/ingredients",
        headers=auth_headers(user),
        files={"file": ("image.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "id" in payload
    assert payload["uploaded_by_id"] == str(user.id)
    assert "file_path" in payload
    assert "uploaded_at" in payload


def test_create_ingredient_non_image_returns_400(client, create_user, auth_headers):
    user = create_user(email="uploader@example.com")
    response = client.post(
        "/ingredients",
        headers=auth_headers(user),
        files={"file": ("file.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_list_ingredients_with_auth(client, create_user, auth_headers):
    user = create_user(email="list@example.com")
    response = client.get("/ingredients", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert "ingredients" in data
    assert "total" in data
    assert data["total"] >= 0


def test_get_ingredient_with_auth(client, create_user, auth_headers, db_session):
    user = create_user(email="getter@example.com")
    # Create one via model so we have a known id
    ing = Ingredient(
        file_path="/tmp/test-image.jpg",
        uploaded_by_id=user.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.get(
        f"/ingredients/{ing.id}",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(ing.id)
    assert response.json()["uploaded_by_id"] == str(user.id)


def test_get_ingredient_not_found_returns_404(client, create_user, auth_headers):
    user = create_user(email="getter@example.com")
    response = client.get(
        "/ingredients/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingredient not found"


def test_delete_ingredient_own_succeeds(client, create_user, auth_headers, db_session):
    user = create_user(email="owner@example.com")
    ing = Ingredient(
        file_path="/tmp/test-delete.jpg",
        uploaded_by_id=user.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.delete(
        f"/ingredients/{ing.id}",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Ingredient deleted"


def test_delete_ingredient_other_returns_403(client, create_user, auth_headers, db_session):
    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    ing = Ingredient(
        file_path="/tmp/test-other.jpg",
        uploaded_by_id=owner.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.delete(
        f"/ingredients/{ing.id}",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    assert "detail" in response.json()


def test_delete_ingredient_other_as_admin_succeeds(
    client, create_user, auth_headers, db_session
):
    admin = create_user(email="admin@example.com", is_admin=True)
    owner = create_user(email="owner@example.com")
    ing = Ingredient(
        file_path="/tmp/test-admin-delete.jpg",
        uploaded_by_id=owner.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.delete(
        f"/ingredients/{ing.id}",
        headers=auth_headers(admin),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Ingredient deleted"


def test_delete_ingredient_not_found_returns_404(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.delete(
        "/ingredients/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingredient not found"


def test_drop_ingredients_db_requires_admin(client, create_user, auth_headers):
    user = create_user(email="regular@example.com")
    response = client.delete(
        "/admin/drop-ingredients-db",
        headers=auth_headers(user),
    )
    assert response.status_code == 403


def test_analyze_ingredient_without_auth_returns_401(
    client, create_user, db_session, auth_headers
):
    from ingredients.models import Ingredient

    user = create_user(email="user@example.com")
    ing = Ingredient(file_path="/tmp/any.jpg", uploaded_by_id=user.id)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.post(f"/ingredients/{ing.id}/analyze")
    assert response.status_code == 401


def test_analyze_ingredient_not_found_returns_404(client, create_user, auth_headers):
    user = create_user(email="user@example.com")
    response = client.post(
        "/ingredients/00000000-0000-0000-0000-000000000000/analyze",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingredient not found"


def test_analyze_ingredient_other_user_returns_403(
    client, create_user, auth_headers, db_session
):
    from ingredients.models import Ingredient

    owner = create_user(email="owner@example.com")
    other = create_user(email="other@example.com")
    ing = Ingredient(file_path="/tmp/other.jpg", uploaded_by_id=owner.id)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.post(
        f"/ingredients/{ing.id}/analyze",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    assert "detail" in response.json()


def test_analyze_ingredient_queues_task(
    client, create_user, auth_headers, db_session, tmp_path
):
    """With mocked task, analyze returns 202 and response includes task_id."""
    from unittest.mock import patch

    from ingredients.models import Ingredient

    user = create_user(email="user@example.com")
    img = tmp_path / "fake.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    ing = Ingredient(file_path=str(img), uploaded_by_id=user.id)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    with patch("ingredients.apis.analyze_ingredient_task") as mock_task:
        mock_task.delay.return_value.id = "mock-task-id"
        response = client.post(
            f"/ingredients/{ing.id}/analyze",
            headers=auth_headers(user),
        )
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Analysis queued"
    assert data["task_id"] == "mock-task-id"
    assert data["ingredient_id"] == str(ing.id)


def test_analyze_ingredient_image_not_found_returns_404(
    client, create_user, auth_headers, db_session
):
    from ingredients.models import Ingredient

    user = create_user(email="user@example.com")
    ing = Ingredient(
        file_path="/nonexistent/path/image.jpg",
        uploaded_by_id=user.id,
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.post(
        f"/ingredients/{ing.id}/analyze",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingredient image not found"


def test_analyze_ingredient_already_completed(
    client, create_user, auth_headers, db_session, tmp_path
):
    from ingredients.models import Ingredient

    user = create_user(email="user@example.com")
    img = tmp_path / "done.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    ing = Ingredient(
        file_path=str(img),
        uploaded_by_id=user.id,
        ingredient_details="some text",
        ingredient_analysis={"key": "value"},
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    response = client.post(
        f"/ingredients/{ing.id}/analyze",
        headers=auth_headers(user),
    )
    assert response.status_code == 202
    data = response.json()
    assert "already completed" in data["message"].lower()
    assert data["ingredient_id"] == str(ing.id)
