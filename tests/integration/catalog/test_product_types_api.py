from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Category, ProductType
from tests.conftest import LoginAs, MakeCategory, MakeProduct, MakeProductType, MakeUser


@pytest.fixture
def hardware(make_category: MakeCategory) -> Category:
    return make_category("Hardware")


def stored_types(db_session: Session) -> list[tuple[str, int]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(ProductType.name, ProductType.category_id).order_by(ProductType.id)
    )
    return [tuple(row) for row in rows]


def create_type(client: FlaskClient, **body: Any) -> Any:
    return client.post("/product-types", json=body)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/categories"),
        ("POST", "/categories"),
        ("PATCH", "/categories/1"),
        ("DELETE", "/categories/1"),
    ],
)
@pytest.mark.parametrize("session", ["admin", "anonymous"])
def test_category_routes_do_not_exist(
    session: str,
    method: str,
    path: str,
    client: FlaskClient,
    make_user: MakeUser,
    login_as: LoginAs,
) -> None:
    """SPEC-PTY-35 · TC-PTY-35a"""
    if session == "admin":
        login_as(client, make_user(role="Admin"))

    response = client.open(path, method=method)

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


def test_admin_creates_a_product_type(admin_client: FlaskClient, hardware: Category) -> None:
    """SPEC-PTY-03 · TC-PTY-03d"""
    response = create_type(admin_client, name="Notebook", category_id=hardware.id)

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "name": "Notebook"}


def test_create_product_type_in_unknown_category_is_not_found(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-PTY-04 · TC-PTY-04c"""
    response = create_type(admin_client, name="Notebook", category_id=9999)

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}
    assert stored_types(db_session) == []


def test_create_product_type_with_a_taken_name_in_the_category_is_a_conflict(
    admin_client: FlaskClient, hardware: Category, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-05 · TC-PTY-05e"""
    make_product_type(hardware, "Notebook")

    response = create_type(admin_client, name="nOTEBOOK", category_id=hardware.id)

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_product_type"}


def test_create_product_type_with_non_text_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, hardware: Category
) -> None:
    """SPEC-PTY-15 · TC-PTY-15h"""
    response = create_type(admin_client, name=123, category_id=hardware.id)

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "invalid"}
    assert stored_types(db_session) == []


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"category_id": "abc"}, "invalid"),
        ({"category_id": True}, "invalid"),
        ({}, "required"),
    ],
)
def test_create_product_type_with_malformed_or_missing_category_id_is_rejected(
    admin_client: FlaskClient,
    db_session: Session,
    hardware: Category,
    body: dict[str, Any],
    reason: str,
) -> None:
    """SPEC-PTY-20 · TC-PTY-20f"""
    response = create_type(admin_client, name="Notebook", **body)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"category_id": reason},
    }
    assert stored_types(db_session) == []


@pytest.fixture
def office(make_category: MakeCategory) -> Category:
    return make_category("Oficina")


@pytest.fixture
def notebook(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Notebook")


def test_admin_renames_and_moves_a_product_type(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, office: Category
) -> None:
    """SPEC-PTY-06 · TC-PTY-06e"""
    response = admin_client.patch(
        f"/product-types/{notebook.id}",
        json={"name": "Ultrabook", "category_id": office.id, "id": 99},
    )

    assert response.status_code == 200
    assert response.get_json() == {"id": notebook.id, "name": "Ultrabook"}
    assert stored_types(db_session) == [("Ultrabook", office.id)]


def test_update_unknown_product_type_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-06 · TC-PTY-06f"""
    response = admin_client.patch("/product-types/9999", json={"name": "X"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


def test_rename_product_type_to_an_empty_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-15 · TC-PTY-15i"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"name": ""})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "required"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_move_product_type_to_unknown_category_is_not_found(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-16 · TC-PTY-16d"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"category_id": 9999})

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_rename_product_type_stores_the_name_without_surrounding_spaces(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-19 · TC-PTY-19d"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"name": "  Ultrabook "})

    assert response.status_code == 200
    assert response.get_json()["name"] == "Ultrabook"
    assert stored_types(db_session) == [("Ultrabook", hardware.id)]


def test_move_product_type_with_malformed_category_id_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-20 · TC-PTY-20g"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"category_id": 0})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"category_id": "invalid"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_admin_deletes_a_product_type(admin_client: FlaskClient, notebook: ProductType) -> None:
    """SPEC-PTY-07 · TC-PTY-07d"""
    response = admin_client.delete(f"/product-types/{notebook.id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert admin_client.get("/product-types").get_json() == []


def test_delete_unknown_product_type_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-07 · TC-PTY-07e"""
    response = admin_client.delete("/product-types/9999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


def test_delete_product_type_with_products_is_a_conflict(
    admin_client: FlaskClient,
    db_session: Session,
    notebook: ProductType,
    hardware: Category,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08c"""
    make_product(notebook, "XPS 13")

    response = admin_client.delete(f"/product-types/{notebook.id}")

    assert response.status_code == 409
    assert response.get_json() == {"error": "product_type_in_use"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


@pytest.fixture
def reference_types(make_category: MakeCategory, make_product_type: MakeProductType) -> None:
    hardware = make_category("Hardware")
    for name in ["Router", "Notebook", "Ruteador USB", "Cámara", "50% off", "access point"]:
        make_product_type(hardware, name)


def listed(response: Any) -> list[tuple[int, str]]:
    return [(item["id"], item["name"]) for item in response.get_json()]


def names(response: Any) -> list[str]:
    return [name for _, name in listed(response)]


ALL_NAMES = ["50% off", "access point", "Cámara", "Notebook", "Router", "Ruteador USB"]


@pytest.mark.usefixtures("reference_types")
def test_any_user_lists_product_types_as_a_flat_array(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser
) -> None:
    """SPEC-PTY-31 · TC-PTY-31c"""
    login_as(client, make_user(role="Client"))

    response = client.get("/product-types")

    assert response.status_code == 200
    assert names(response) == ALL_NAMES
    assert all(isinstance(item["id"], int) for item in response.get_json())


@pytest.mark.usefixtures("reference_types")
def test_listing_product_types_filters_by_q(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser
) -> None:
    """SPEC-PTY-32 · TC-PTY-32c"""
    login_as(client, make_user(role="Representative"))

    response = client.get("/product-types?q=ute")

    assert response.status_code == 200
    assert names(response) == ["Router", "Ruteador USB"]


@pytest.mark.usefixtures("reference_types")
@pytest.mark.parametrize("query", ["q=", "q=%20"])
def test_listing_product_types_with_blank_q_equals_no_q(
    query: str, client: FlaskClient, login_as: LoginAs, make_user: MakeUser
) -> None:
    """SPEC-PTY-32 · TC-PTY-32d"""
    login_as(client, make_user(role="Representative"))

    response = client.get(f"/product-types?{query}")

    assert response.status_code == 200
    assert names(response) == ALL_NAMES


@pytest.mark.usefixtures("reference_types")
@pytest.mark.parametrize("query", ["page=abc", "page=1&page_size=1", "q=UTE&page=2"])
def test_listing_product_types_is_never_paginated(
    query: str, client: FlaskClient, login_as: LoginAs, make_user: MakeUser
) -> None:
    """SPEC-PTY-33 · TC-PTY-33a"""
    login_as(client, make_user(role="Representative"))

    response = client.get(f"/product-types?{query}")

    assert response.status_code == 200
    expected = ["Router", "Ruteador USB"] if query.startswith("q=") else ALL_NAMES
    assert names(response) == expected


@pytest.mark.usefixtures("reference_types")
@pytest.mark.parametrize("query", ["category_id=abc", "category_id=9999"])
def test_listing_product_types_ignores_category_id(query: str, admin_client: FlaskClient) -> None:
    """SPEC-PTY-35 · TC-PTY-35b"""
    response = admin_client.get(f"/product-types?{query}")

    assert response.status_code == 200
    assert names(response) == ALL_NAMES


def test_every_product_type_response_has_exactly_id_and_name(
    admin_client: FlaskClient, hardware: Category, notebook: ProductType
) -> None:
    """SPEC-PTY-35 · TC-PTY-35c"""
    listing = admin_client.get("/product-types")
    created = create_type(admin_client, name="Router", category_id=hardware.id)
    updated = admin_client.patch(f"/product-types/{notebook.id}", json={"name": "Ultrabook"})

    assert [response.status_code for response in (listing, created, updated)] == [200, 201, 200]
    assert [set(item) for item in listing.get_json()] == [{"id", "name"}]
    assert set(created.get_json()) == {"id", "name"}
    assert set(updated.get_json()) == {"id", "name"}
