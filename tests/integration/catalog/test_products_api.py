from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Product, ProductType
from tests.conftest import LoginAs, MakeProduct, MakeProductType, MakeUser


@pytest.fixture
def notebook(make_product_type: MakeProductType) -> ProductType:
    return make_product_type(name="Notebook")


def stored_products(db_session: Session) -> list[tuple[str, int, bool]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(Product.name, Product.product_type_id, Product.is_active).order_by(Product.id)
    )
    return [tuple(row) for row in rows]


def create_product(client: FlaskClient, **body: Any) -> Any:
    return client.post("/products", json=body)


def test_admin_creates_a_product(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType
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
        "product_type": {"id": notebook.id, "name": "Notebook"},
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
def rosa_client(client: FlaskClient, make_user: MakeUser, login_as: LoginAs) -> FlaskClient:
    login_as(client, make_user(role="Representative"))
    return client


def test_representative_creates_a_product(
    rosa_client: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-35 · TC-PRD-35c"""
    response = create_product(rosa_client, name="  XPS 15 ", product_type_id=notebook.id)

    assert response.status_code == 201
    body = response.get_json()
    assert body == {
        "id": body["id"],
        "name": "XPS 15",
        "is_active": True,
        "product_type": {"id": notebook.id, "name": "Notebook"},
    }
    assert isinstance(body["id"], int)
    assert stored_products(db_session) == [("XPS 15", notebook.id, True)]


def test_representative_creating_a_product_gets_the_admin_errors(
    rosa_client: FlaskClient, db_session: Session, notebook: ProductType, make_product: MakeProduct
) -> None:
    """SPEC-PRD-35 · TC-PRD-35d"""
    make_product(notebook, "xps 13")
    before = stored_products(db_session)

    nameless = create_product(rosa_client, product_type_id=notebook.id)
    unknown = create_product(rosa_client, name="XPS 15", product_type_id=9999)
    duplicate = create_product(rosa_client, name="XPS 13", product_type_id=notebook.id)

    assert nameless.status_code == 400
    assert nameless.get_json()["fields"] == {"name": "required"}
    assert unknown.status_code == 404
    assert unknown.get_json() == {"error": "product_type_not_found"}
    assert duplicate.status_code == 409
    assert duplicate.get_json() == {"error": "duplicate_product"}
    assert stored_products(db_session) == before


def test_a_product_created_by_a_representative_is_available(
    rosa_client: FlaskClient, notebook: ProductType
) -> None:
    """SPEC-PRD-35 · TC-PRD-35e"""
    create_product(rosa_client, name="XPS 15", product_type_id=notebook.id)

    response = rosa_client.get("/products/available?q=xps 15")

    assert response.status_code == 200
    assert [product["name"] for product in response.get_json()] == ["XPS 15"]


@pytest.fixture
def client_session(client: FlaskClient, make_user: MakeUser, login_as: LoginAs) -> FlaskClient:
    login_as(client, make_user(role="Client"))
    return client


def test_client_cannot_create_a_product(
    client_session: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-37 · TC-PRD-37d"""
    response = create_product(client_session, name="XPS 15", product_type_id=notebook.id)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert stored_products(db_session) == []


def test_malformed_body_of_a_client_is_a_400_not_a_403(
    client_session: FlaskClient, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-37 · TC-PRD-37e"""
    response = create_product(client_session, product_type_id="abc")

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "required", "product_type_id": "invalid"}
    assert stored_products(db_session) == []


def test_client_creating_in_an_unknown_type_gets_forbidden_not_not_found(
    client_session: FlaskClient, db_session: Session
) -> None:
    """SPEC-PRD-37 · TC-PRD-37f"""
    response = create_product(client_session, name="XPS 15", product_type_id=9999)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert stored_products(db_session) == []


@pytest.fixture
def catalog(make_product_type: MakeProductType, make_product: MakeProduct) -> dict[str, Any]:
    """`xps 13` (Notebook), inactive `Optiplex` (Desktop) and `LaserJet` (Impresora)."""
    notebook = make_product_type(name="Notebook")
    desktop = make_product_type(name="Desktop")
    printer = make_product_type(name="Impresora")
    return {
        "notebook": notebook,
        "printer": printer,
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
        "product_type": {"id": product_type.id, "name": product_type.name},
    }


def listed_names(response: Any) -> list[str]:
    return [product["name"] for product in response.get_json()]


def logged_in_as(role: str, client: FlaskClient, make_user: MakeUser, login_as: LoginAs) -> Any:
    login_as(client, make_user(role=role))
    return client


def test_any_user_lists_every_product_with_its_type_and_state(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-31 · TC-PRD-31d"""
    expected = [expected_json(product) for product in catalog["products"]]

    response = logged_in_as("Client", client, make_user, login_as).get("/products")

    assert response.status_code == 200
    assert response.get_json() == expected
    assert [set(item) for item in response.get_json()] == [
        {"id", "name", "is_active", "product_type"}
    ] * 3
    assert [set(item["product_type"]) for item in response.get_json()] == [{"id", "name"}] * 3
    assert response.get_json()[1]["is_active"] is False


def test_products_can_be_filtered_by_type(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-32 · TC-PRD-32c"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    response = rep.get(f"/products?product_type_id={catalog['notebook'].id}")

    assert response.status_code == 200
    assert listed_names(response) == ["xps 13"]


@pytest.mark.parametrize(
    ("query", "names"),
    [
        ("category_id=abc", ["LaserJet", "Optiplex", "xps 13"]),
        ("category_id=9999", ["LaserJet", "Optiplex", "xps 13"]),
        ("category_id=1&product_type_id={notebook}", ["xps 13"]),
    ],
)
def test_listing_products_ignores_category_id(
    query: str,
    names: list[str],
    admin_client: FlaskClient,
    catalog: dict[str, Any],
) -> None:
    """SPEC-PRD-32 · TC-PRD-32d"""
    response = admin_client.get("/products?" + query.format(notebook=catalog["notebook"].id))

    assert response.status_code == 200
    assert listed_names(response) == names


@pytest.mark.parametrize("query", ["product_type_id=", "product_type_id=0"])
def test_listing_products_with_a_malformed_type_filter_is_rejected(
    admin_client: FlaskClient, query: str
) -> None:
    """SPEC-PRD-33 · TC-PRD-33h"""
    response = admin_client.get(f"/products?{query}")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"product_type_id": "invalid"},
    }


def test_listing_products_of_unknown_type_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PRD-34 · TC-PRD-34b"""
    response = admin_client.get("/products?product_type_id=9999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


def test_listing_products_of_a_type_beyond_sqlite_integers_is_not_found(
    admin_client: FlaskClient,
) -> None:
    """SPEC-PRD-34 · TC-PRD-34c"""
    response = admin_client.get("/products?product_type_id=99999999999999999999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


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
def desktop(make_product_type: MakeProductType) -> ProductType:
    return make_product_type(name="Desktop")


@pytest.fixture
def xps(notebook: ProductType, make_product: MakeProduct) -> Product:
    return make_product(notebook, "XPS 13")


def test_admin_renames_and_moves_a_product_ignoring_other_keys(
    admin_client: FlaskClient,
    db_session: Session,
    xps: Product,
    desktop: ProductType,
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
        "product_type": {"id": desktop.id, "name": "Desktop"},
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


def test_admin_activates_an_inactive_product(
    admin_client: FlaskClient, db_session: Session, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-22 · TC-PRD-22c"""
    optiplex = catalog["products"][1]

    response = admin_client.post(f"/products/{optiplex.id}/activate")

    assert response.status_code == 200
    assert response.get_json() == expected_json(optiplex) | {"is_active": True}
    assert response.get_json()["is_active"] is True
    assert ("Optiplex", optiplex.product_type_id, True) in stored_products(db_session)


def test_an_activated_product_is_available_again(
    client: FlaskClient,
    admin_client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    catalog: dict[str, Any],
) -> None:
    """SPEC-PRD-22 · TC-PRD-22d"""
    admin_client.post(f"/products/{catalog['products'][1].id}/activate")

    response = logged_in_as("Representative", client, make_user, login_as).get(
        "/products/available"
    )

    assert "Optiplex" in listed_names(response)


def test_activate_an_active_product_succeeds(
    admin_client: FlaskClient, catalog: dict[str, Any]
) -> None:
    """SPEC-PRD-23 · TC-PRD-23b"""
    response = admin_client.post(f"/products/{catalog['products'][2].id}/activate")

    assert response.status_code == 200
    assert response.get_json()["is_active"] is True


@pytest.mark.parametrize("product_id", ["9999", "9223372036854775808"])
def test_activate_unknown_product_is_not_found(admin_client: FlaskClient, product_id: str) -> None:
    """SPEC-PRD-24 · TC-PRD-24b"""
    response = admin_client.post(f"/products/{product_id}/activate")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_found"}


@pytest.fixture
def searchable(catalog: dict[str, Any], make_product: MakeProduct) -> dict[str, Any]:
    """The `catalog` data plus `XPS 15` (Notebook), `Cámara IP` and `50% Toner` (Impresora)."""
    printer = catalog["products"][0].product_type
    make_product(catalog["notebook"], "XPS 15")
    make_product(printer, "Cámara IP")
    make_product(printer, "50% Toner")
    return catalog


def test_products_are_searched_by_text_alone_and_with_other_filters(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-26 · TC-PRD-26e"""
    user = logged_in_as("Client", client, make_user, login_as)

    by_text = user.get("/products?q=XPS")
    with_type = user.get(f"/products?q=xps&product_type_id={searchable['printer'].id}")

    assert by_text.status_code == 200
    assert listed_names(by_text) == ["xps 13", "XPS 15"]
    assert with_type.status_code == 200
    assert with_type.get_json() == []


def test_a_blank_search_text_lists_every_product(
    admin_client: FlaskClient, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-26 · TC-PRD-26g"""
    everything = admin_client.get("/products")

    response = admin_client.get("/products?q=")

    assert response.status_code == 200
    assert response.get_json() == everything.get_json()
    assert len(response.get_json()) == 6


def test_products_are_filtered_by_state(
    admin_client: FlaskClient, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-27 · TC-PRD-27c"""
    inactive = admin_client.get("/products?is_active=false")
    active_search = admin_client.get("/products?is_active=true&q=xps")

    assert inactive.status_code == 200
    assert listed_names(inactive) == ["Optiplex"]
    assert inactive.get_json()[0]["is_active"] is False
    assert active_search.status_code == 200
    assert listed_names(active_search) == ["xps 13", "XPS 15"]


@pytest.mark.parametrize("query", ["is_active=yes", "is_active="])
def test_listing_products_with_a_malformed_state_is_rejected(
    admin_client: FlaskClient, query: str
) -> None:
    """SPEC-PRD-28 · TC-PRD-28b"""
    response = admin_client.get(f"/products?{query}")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"is_active": "invalid"},
    }


def test_products_are_paged(admin_client: FlaskClient, searchable: dict[str, Any]) -> None:
    """SPEC-PRD-29 · TC-PRD-29d"""
    first = admin_client.get("/products?page=1&page_size=2")
    second = admin_client.get("/products?page=2")

    assert first.status_code == 200
    assert first.get_json()["page"] == 1
    assert first.get_json()["page_size"] == 2
    assert first.get_json()["total"] == 6
    assert [item["name"] for item in first.get_json()["items"]] == ["50% Toner", "Cámara IP"]
    assert second.get_json() == {"items": [], "page": 2, "page_size": 20, "total": 6}


def test_a_page_beyond_the_last_one_is_empty(
    admin_client: FlaskClient, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-29 · TC-PRD-29f"""
    response = admin_client.get("/products?page=50&page_size=10")

    assert response.status_code == 200
    assert response.get_json() == {"items": [], "page": 50, "page_size": 10, "total": 6}


def test_listing_products_with_a_malformed_page_is_rejected(admin_client: FlaskClient) -> None:
    """SPEC-PRD-29 · TC-PRD-29h"""
    response = admin_client.get("/products?page=abc")

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"page": "invalid"}}


def test_available_products_are_searched_by_text(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-26 · TC-PRD-26f"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    response = rep.get("/products/available?q=xps")

    assert response.status_code == 200
    assert listed_names(response) == ["xps 13", "XPS 15"]


def test_available_products_with_a_blank_search_text_are_all_listed(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-26 · TC-PRD-26g"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    response = rep.get("/products/available?q=%20%20")

    assert response.status_code == 200
    assert response.get_json() == rep.get("/products/available").get_json()
    assert len(response.get_json()) == 5


def test_available_products_are_paged(
    client: FlaskClient, login_as: LoginAs, make_user: MakeUser, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-29 · TC-PRD-29g"""
    rep = logged_in_as("Representative", client, make_user, login_as)

    toner = next(
        product
        for product in searchable["products"][0].product_type.products
        if product.name == "50% Toner"
    )

    response = rep.get("/products/available?page=1&page_size=1")

    assert response.status_code == 200
    assert response.get_json() == {
        "items": [expected_json(toner)],
        "page": 1,
        "page_size": 1,
        "total": 5,
    }


def test_listing_available_products_with_a_malformed_page_size_is_rejected(
    admin_client: FlaskClient,
) -> None:
    """SPEC-PRD-29 · TC-PRD-29h"""
    response = admin_client.get("/products/available?page_size=0")

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"page_size": "invalid"}}


def test_available_products_ignore_every_other_parameter(
    admin_client: FlaskClient, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-30 · TC-PRD-30a"""
    plain = admin_client.get("/products/available")

    response = admin_client.get(
        "/products/available?is_active=false&category_id=abc&product_type_id=0&foo=1"
    )

    assert response.status_code == 200
    assert response.get_json() == plain.get_json()
    assert len(response.get_json()) == 5


def test_available_products_apply_the_search_and_ignore_the_category_id(
    admin_client: FlaskClient, searchable: dict[str, Any]
) -> None:
    """SPEC-PRD-30 · TC-PRD-30b"""
    response = admin_client.get("/products/available?q=xps&category_id=1")

    assert response.status_code == 200
    assert listed_names(response) == ["xps 13", "XPS 15"]
