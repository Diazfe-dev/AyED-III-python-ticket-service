from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Category, Product, ProductType
from tests.conftest import LoginAs, MakeCategory, MakeProduct, MakeProductType, MakeUser


@pytest.fixture
def hardware(make_category: MakeCategory) -> Category:
    return make_category("Hardware")


@pytest.fixture
def notebook(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Notebook")


def stored_products(db_session: Session) -> list[tuple[str, int, bool]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(Product.name, Product.product_type_id, Product.is_active).order_by(Product.id)
    )
    return [tuple(row) for row in rows]


def create_product(client: FlaskClient, **body: Any) -> Any:
    return client.post("/products", json=body)


def test_admin_creates_a_product(
    admin_client: FlaskClient, db_session: Session, hardware: Category, notebook: ProductType
) -> None:
    """SPEC-PRD-01 · TC-PRD-01d"""
    response = create_product(admin_client, name="XPS 13", product_type_id=notebook.id)

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body == {
        "id": body["id"],
        "name": "XPS 13",
        "is_active": True,
        "product_type": {"id": notebook.id, "name": "Notebook", "category_id": hardware.id},
        "category": {"id": hardware.id, "name": "Hardware"},
    }
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


def test_create_product_of_unknown_type_is_not_found(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-PRD-02 · TC-PRD-02b"""
    response = create_product(admin_client, name="XPS 13", product_type_id=9999)

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}
    assert stored_products(db_session) == []


def test_create_product_of_a_type_beyond_sqlite_integers_is_not_found(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-PRD-02 · TC-PRD-02c"""
    response = create_product(admin_client, name="XPS 13", product_type_id=2**63)

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}
    assert stored_products(db_session) == []


def test_create_product_without_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-03 · TC-PRD-03b"""
    response = create_product(admin_client, product_type_id=notebook.id)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"name": "required"}}
    assert stored_products(db_session) == []


def test_create_product_with_non_text_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-11 · TC-PRD-11c"""
    response = create_product(admin_client, name=123, product_type_id=notebook.id)

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "invalid"}
    assert stored_products(db_session) == []


def test_create_product_with_a_taken_name_in_the_type_is_a_conflict(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-13 · TC-PRD-13g"""
    create_product(admin_client, name="XPS 13", product_type_id=notebook.id)

    response = create_product(admin_client, name="xPS 13", product_type_id=notebook.id)

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_product"}
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


def test_create_product_stores_the_name_without_surrounding_spaces(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-14 · TC-PRD-14b"""
    response = create_product(admin_client, name="  XPS 13 ", product_type_id=notebook.id)

    assert response.status_code == 201
    assert response.get_json()["name"] == "XPS 13"
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"product_type_id": "abc"}, "invalid"),
        ({"product_type_id": True}, "invalid"),
        ({}, "required"),
    ],
)
def test_create_product_with_malformed_or_missing_product_type_id_is_rejected(
    admin_client: FlaskClient, db_session: Session, body: dict[str, Any], reason: str
) -> None:
    """SPEC-PRD-15 · TC-PRD-15f"""
    response = create_product(admin_client, name="XPS 13", **body)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"product_type_id": reason},
    }
    assert stored_products(db_session) == []


@pytest.fixture
def catalog(
    make_category: MakeCategory, make_product_type: MakeProductType, make_product: MakeProduct
) -> dict[str, Any]:
    """`xps 13` (Notebook), inactive `Optiplex` (Desktop) and `LaserJet` (Impresora, Oficina)."""
    hardware, office = make_category("Hardware"), make_category("Oficina")
    notebook = make_product_type(hardware, "Notebook")
    desktop = make_product_type(hardware, "Desktop")
    printer = make_product_type(office, "Impresora")
    return {
        "hardware": hardware,
        "office": office,
        "notebook": notebook,
        "products": [
            make_product(printer, "LaserJet"),
            make_product(desktop, "Optiplex", is_active=False),
            make_product(notebook, "xps 13"),
        ],
    }


def expected_json(product: Product) -> dict[str, Any]:
    product_type = product.product_type
    return {
        "id": product.id,
        "name": product.name,
        "is_active": product.is_active,
        "product_type": {
            "id": product_type.id,
            "name": product_type.name,
            "category_id": product_type.category_id,
        },
        "category": {"id": product_type.category.id, "name": product_type.category.name},
    }


def listed_names(response: Any) -> list[str]:
    return [product["name"] for product in response.get_json()]


def logged_in_as(role: str, client: FlaskClient, make_user: MakeUser, login_as: LoginAs) -> Any:
    login_as(client, make_user(role=role))
    return client


def test_any_user_lists_every_product_with_type_category_and_state(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-07 · TC-PRD-07d"""
    expected = [expected_json(product) for product in catalog["products"]]

    response = logged_in_as("Client", client, make_user, login_as).get("/products")

    assert response.status_code == 200
    assert response.get_json() == expected
    assert response.get_json()[1]["is_active"] is False


def test_products_can_be_filtered_by_category_or_type(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-08 · TC-PRD-08g"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    by_category = rep.get(f"/products?category_id={catalog['hardware'].id}")
    by_type = rep.get(f"/products?product_type_id={catalog['notebook'].id}")

    assert by_category.status_code == 200
    assert listed_names(by_category) == ["Optiplex", "xps 13"]
    assert by_type.status_code == 200
    assert listed_names(by_type) == ["xps 13"]


def test_filtering_by_a_type_outside_the_category_lists_nothing(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-20 · TC-PRD-20c"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    response = rep.get(
        f"/products?category_id={catalog['office'].id}&product_type_id={catalog['notebook'].id}"
    )

    assert response.status_code == 200
    assert response.get_json() == []


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        ("category_id=abc", {"category_id": "invalid"}),
        ("product_type_id=", {"product_type_id": "invalid"}),
        (
            "category_id=x&product_type_id=0",
            {"category_id": "invalid", "product_type_id": "invalid"},
        ),
    ],
)
def test_listing_products_with_malformed_filters_is_rejected(
    admin_client: FlaskClient, query: str, fields: dict[str, str]
) -> None:
    """SPEC-PRD-15 · TC-PRD-15h"""
    response = admin_client.get(f"/products?{query}")

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": fields}


@pytest.mark.parametrize(
    ("query", "error"),
    [
        ("category_id=9999", "category_not_found"),
        ("product_type_id=9999", "product_type_not_found"),
    ],
)
def test_listing_products_of_unknown_category_or_type_is_not_found(
    admin_client: FlaskClient, query: str, error: str
) -> None:
    """SPEC-PRD-16 · TC-PRD-16c"""
    response = admin_client.get(f"/products?{query}")

    assert response.status_code == 404
    assert response.get_json() == {"error": error}


@pytest.mark.parametrize(
    ("field", "error"),
    [("category_id", "category_not_found"), ("product_type_id", "product_type_not_found")],
)
def test_listing_products_with_a_filter_beyond_sqlite_integers_is_not_found(
    admin_client: FlaskClient, field: str, error: str
) -> None:
    """SPEC-PRD-16 · TC-PRD-16d"""
    response = admin_client.get(f"/products?{field}=99999999999999999999")

    assert response.status_code == 404
    assert response.get_json() == {"error": error}


@pytest.mark.parametrize("role", ["Client", "Representative"])
def test_any_user_lists_only_the_available_products(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    catalog: dict[str, Any],
    role: str,
) -> None:
    """SPEC-PRD-10 · TC-PRD-10c"""
    response = logged_in_as(role, client, make_user, login_as).get("/products/available")

    assert response.status_code == 200
    assert listed_names(response) == ["LaserJet", "xps 13"]
    assert all(product["is_active"] for product in response.get_json())


@pytest.fixture
def desktop(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Desktop")


@pytest.fixture
def xps(notebook: ProductType, make_product: MakeProduct) -> Product:
    return make_product(notebook, "XPS 13")


def test_admin_renames_and_moves_a_product_ignoring_other_keys(
    admin_client: FlaskClient,
    db_session: Session,
    xps: Product,
    desktop: ProductType,
    hardware: Category,
) -> None:
    """SPEC-PRD-04 · TC-PRD-04g"""
    response = admin_client.patch(
        f"/products/{xps.id}",
        json={"name": "Optiplex", "product_type_id": desktop.id, "id": 99, "is_active": False},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "id": xps.id,
        "name": "Optiplex",
        "is_active": True,
        "product_type": {"id": desktop.id, "name": "Desktop", "category_id": hardware.id},
        "category": {"id": hardware.id, "name": "Hardware"},
    }
    assert stored_products(db_session) == [("Optiplex", desktop.id, True)]


def test_rename_product_to_an_empty_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, xps: Product, notebook: ProductType
) -> None:
    """SPEC-PRD-11 · TC-PRD-11d"""
    response = admin_client.patch(f"/products/{xps.id}", json={"name": ""})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "required"}
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


def test_move_product_to_unknown_type_is_not_found(
    admin_client: FlaskClient, db_session: Session, xps: Product, notebook: ProductType
) -> None:
    """SPEC-PRD-12 · TC-PRD-12b"""
    response = admin_client.patch(f"/products/{xps.id}", json={"product_type_id": 9999})

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


def test_rename_product_to_a_taken_name_is_a_conflict(
    admin_client: FlaskClient,
    db_session: Session,
    xps: Product,
    notebook: ProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PRD-13 · TC-PRD-13h"""
    xps15 = make_product(notebook, "XPS 15")

    response = admin_client.patch(f"/products/{xps15.id}", json={"name": "xps 13"})

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_product"}
    assert stored_products(db_session) == [
        ("XPS 13", notebook.id, True),
        ("XPS 15", notebook.id, True),
    ]


def test_rename_product_stores_the_name_without_surrounding_spaces(
    admin_client: FlaskClient, db_session: Session, xps: Product, notebook: ProductType
) -> None:
    """SPEC-PRD-14 · TC-PRD-14c"""
    response = admin_client.patch(f"/products/{xps.id}", json={"name": "  XPS 15 "})

    assert response.status_code == 200
    assert response.get_json()["name"] == "XPS 15"
    assert stored_products(db_session) == [("XPS 15", notebook.id, True)]


def test_move_product_with_malformed_product_type_id_is_rejected(
    admin_client: FlaskClient, db_session: Session, xps: Product, notebook: ProductType
) -> None:
    """SPEC-PRD-15 · TC-PRD-15g"""
    response = admin_client.patch(f"/products/{xps.id}", json={"product_type_id": 0})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"product_type_id": "invalid"}
    assert stored_products(db_session) == [("XPS 13", notebook.id, True)]


def test_update_unknown_product_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PRD-17 · TC-PRD-17d"""
    response = admin_client.patch("/products/9999", json={"name": "X"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_found"}


def test_update_product_beyond_sqlite_integers_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PRD-17 · TC-PRD-17e"""
    response = admin_client.patch("/products/9223372036854775808", json={"name": "X"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_found"}


def test_update_inactive_product_keeps_it_inactive(
    admin_client: FlaskClient,
    db_session: Session,
    notebook: ProductType,
    desktop: ProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PRD-19 · TC-PRD-19b"""
    product = make_product(notebook, "XPS 13", is_active=False)

    response = admin_client.patch(
        f"/products/{product.id}", json={"name": "XPS 15", "product_type_id": desktop.id}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert (body["name"], body["product_type"]["id"], body["is_active"]) == (
        "XPS 15",
        desktop.id,
        False,
    )
    assert stored_products(db_session) == [("XPS 15", desktop.id, False)]


def test_admin_deactivates_a_product(admin_client: FlaskClient, xps: Product) -> None:
    """SPEC-PRD-05 · TC-PRD-05e"""
    response = admin_client.post(f"/products/{xps.id}/deactivate")

    assert response.status_code == 200
    assert response.get_json() == expected_json(xps) | {"is_active": False}


def test_deactivated_product_row_is_kept(
    admin_client: FlaskClient, db_session: Session, xps: Product, notebook: ProductType
) -> None:
    """SPEC-PRD-06 · TC-PRD-06a"""
    admin_client.post(f"/products/{xps.id}/deactivate")

    assert stored_products(db_session) == [("XPS 13", notebook.id, False)]


def test_no_products_route_accepts_delete(app: Flask) -> None:
    """SPEC-PRD-06 · TC-PRD-06c"""
    rules = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/products")]

    assert rules
    assert all("DELETE" not in rule.methods for rule in rules)


@pytest.mark.parametrize("product_id", ["9999", "9223372036854775808"])
def test_deactivate_unknown_product_is_not_found(
    admin_client: FlaskClient, product_id: str
) -> None:
    """SPEC-PRD-17 · TC-PRD-17f"""
    response = admin_client.post(f"/products/{product_id}/deactivate")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_found"}


def test_deactivate_an_inactive_product_succeeds(
    admin_client: FlaskClient, notebook: ProductType, make_product: MakeProduct
) -> None:
    """SPEC-PRD-18 · TC-PRD-18b"""
    product = make_product(notebook, "XPS 13", is_active=False)

    response = admin_client.post(f"/products/{product.id}/deactivate")

    assert response.status_code == 200
    assert response.get_json()["is_active"] is False
