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
