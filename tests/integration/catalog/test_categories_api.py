from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Category, ProductType
from tests.conftest import LoginAs, MakeCategory, MakeProductType, MakeUser


def stored_names(db_session: Session) -> list[str]:
    db_session.expire_all()
    return list(db_session.scalars(select(Category.name).order_by(Category.id)))


def test_admin_creates_a_category(admin_client: FlaskClient, db_session: Session) -> None:
    """SPEC-PTY-01 · TC-PTY-01c"""
    response = admin_client.post("/categories", json={"name": "Hardware"})

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "name": "Hardware"}
    assert stored_names(db_session) == ["Hardware"]


def test_create_category_with_a_taken_name_is_a_conflict(
    admin_client: FlaskClient, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-02 · TC-PTY-02h"""
    make_category("Hardware")

    response = admin_client.post("/categories", json={"name": "HARDWARE"})

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_category"}
    assert stored_names(db_session) == ["Hardware"]


@pytest.mark.parametrize(
    ("body", "reason"),
    [({"name": ""}, "required"), ({"name": 123}, "invalid"), (None, "required")],
)
def test_create_category_with_invalid_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, body: Any, reason: str
) -> None:
    """SPEC-PTY-15 · TC-PTY-15f"""
    response = admin_client.post("/categories", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"name": reason}}
    assert stored_names(db_session) == []


def test_create_category_stores_the_name_without_surrounding_spaces(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-PTY-19 · TC-PTY-19c"""
    response = admin_client.post("/categories", json={"name": "  Hardware "})

    assert response.status_code == 201
    assert response.get_json()["name"] == "Hardware"
    assert stored_names(db_session) == ["Hardware"]


def test_any_user_lists_categories_ordered_by_name(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, make_category: MakeCategory
) -> None:
    """SPEC-PTY-17 · TC-PTY-17c"""
    ids = {name: make_category(name).id for name in ["redes", "Audio", "hardware"]}
    login_as(client, make_user(role="Client"))

    response = client.get("/categories")

    assert response.status_code == 200
    assert response.get_json() == [
        {"id": ids[name], "name": name} for name in ["Audio", "hardware", "redes"]
    ]


def test_rename_category_to_a_name_taken_by_another_is_a_conflict(
    admin_client: FlaskClient, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-02 · TC-PTY-02i"""
    make_category("Hardware")
    redes = make_category("Redes")

    response = admin_client.patch(f"/categories/{redes.id}", json={"name": "hardware"})

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_category"}
    assert stored_names(db_session) == ["Hardware", "Redes"]


def test_admin_renames_a_category(
    admin_client: FlaskClient, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-12 · TC-PTY-12d"""
    category = make_category("Hardware")

    response = admin_client.patch(f"/categories/{category.id}", json={"name": "Redes"})

    assert response.status_code == 200
    assert response.get_json() == {"id": category.id, "name": "Redes"}
    assert stored_names(db_session) == ["Redes"]


def test_rename_unknown_category_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-12 · TC-PTY-12e"""
    response = admin_client.patch("/categories/9999", json={"name": "Redes"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}


def test_rename_category_to_a_blank_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-15 · TC-PTY-15g"""
    category = make_category("Hardware")

    response = admin_client.patch(f"/categories/{category.id}", json={"name": "  "})

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"name": "required"}}
    assert stored_names(db_session) == ["Hardware"]


def test_admin_deletes_a_category_without_types(
    admin_client: FlaskClient, make_category: MakeCategory
) -> None:
    """SPEC-PTY-13 · TC-PTY-13d"""
    category = make_category("Hardware")

    response = admin_client.delete(f"/categories/{category.id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert admin_client.get("/categories").get_json() == []


def test_delete_unknown_category_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-13 · TC-PTY-13e"""
    response = admin_client.delete("/categories/9999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}


def test_delete_category_with_types_is_a_conflict_with_the_reason(
    admin_client: FlaskClient,
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
) -> None:
    """SPEC-PTY-14 · TC-PTY-14e"""
    category = make_category("Hardware")
    product_type = make_product_type(category, "Notebook")

    response = admin_client.delete(f"/categories/{category.id}")

    assert response.status_code == 409
    assert response.get_json() == {"error": "category_in_use"}
    db_session.expire_all()
    assert db_session.get(Category, category.id) is not None
    assert db_session.get(ProductType, product_type.id) is not None
