from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Product, ProductType
from tests.conftest import LoginAs, MakeProduct, MakeProductType, MakeUser

# (method, path, body); `{type}` is the id of the type of the `catalog` fixture.
WRITE_ENDPOINTS = [
    ("POST", "/product-types", {"name": "Router"}),
    ("PATCH", "/product-types/{type}", {"name": "Ultrabook"}),
    ("DELETE", "/product-types/{type}", None),
]

Snapshot = list[tuple[Any, ...]]


@pytest.fixture
def catalog(make_product_type: MakeProductType) -> dict[str, int]:
    """The type `Notebook`."""
    return {"type": make_product_type(name="Notebook").id}


def snapshot(db_session: Session) -> Snapshot:
    db_session.expire_all()
    types = db_session.execute(select(ProductType.id, ProductType.name).order_by(ProductType.id))
    return [tuple(row) for row in types]


def call_as(
    role: str,
    endpoint: tuple[str, str, Any],
    catalog: dict[str, int],
    client: FlaskClient,
    make_user: MakeUser,
    login_as: LoginAs,
) -> Any:
    method, path, body = endpoint
    login_as(client, make_user(role=role))
    return client.open(path.format(**catalog), method=method, json=body)


@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS)
def test_representative_cannot_change_the_catalog(
    endpoint: tuple[str, str, Any],
    catalog: dict[str, int],
    client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    login_as: LoginAs,
) -> None:
    """SPEC-PTY-34 · TC-PTY-34a"""
    before = snapshot(db_session)

    response = call_as("Representative", endpoint, catalog, client, make_user, login_as)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert snapshot(db_session) == before


@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS)
def test_client_cannot_change_the_catalog(
    endpoint: tuple[str, str, Any],
    catalog: dict[str, int],
    client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    login_as: LoginAs,
) -> None:
    """SPEC-PTY-34 · TC-PTY-34b"""
    before = snapshot(db_session)

    response = call_as("Client", endpoint, catalog, client, make_user, login_as)

    assert response.status_code == 403
    assert snapshot(db_session) == before


# (method, path, body); `{product}` is the id of the product of the `products` fixture.
PRODUCT_WRITE_ENDPOINTS = [
    ("PATCH", "/products/{product}", {"name": "XPS 15"}),
    ("POST", "/products/{product}/deactivate", None),
]


@pytest.fixture
def products(make_product_type: MakeProductType, make_product: MakeProduct) -> dict[str, int]:
    """The type `Notebook` and its product `XPS 13`."""
    notebook = make_product_type(name="Notebook")
    return {"type": notebook.id, "product": make_product(notebook, "XPS 13").id}


def product_rows(db_session: Session) -> list[tuple[Any, ...]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(Product.id, Product.name, Product.product_type_id, Product.is_active).order_by(
            Product.id
        )
    )
    return [tuple(row) for row in rows]


def call_product_endpoint_as(
    role: str,
    endpoint: tuple[str, str, Any],
    products: dict[str, int],
    client: FlaskClient,
    make_user: MakeUser,
    login_as: LoginAs,
) -> Any:
    method, path, body = endpoint
    login_as(client, make_user(role=role))
    return client.open(path.format(**products), method=method, json=body)


@pytest.mark.parametrize("endpoint", PRODUCT_WRITE_ENDPOINTS)
def test_representative_cannot_change_products(
    endpoint: tuple[str, str, Any],
    products: dict[str, int],
    client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    login_as: LoginAs,
) -> None:
    """SPEC-PRD-09 · TC-PRD-09a"""
    before = product_rows(db_session)

    response = call_product_endpoint_as(
        "Representative", endpoint, products, client, make_user, login_as
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert product_rows(db_session) == before


@pytest.mark.parametrize("endpoint", PRODUCT_WRITE_ENDPOINTS)
def test_client_cannot_change_products(
    endpoint: tuple[str, str, Any],
    products: dict[str, int],
    client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    login_as: LoginAs,
) -> None:
    """SPEC-PRD-09 · TC-PRD-09b"""
    before = product_rows(db_session)

    response = call_product_endpoint_as("Client", endpoint, products, client, make_user, login_as)

    assert response.status_code == 403
    assert product_rows(db_session) == before


@pytest.mark.parametrize("role", ["Representative", "Client"])
def test_only_an_admin_can_activate_a_product(
    role: str,
    client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    login_as: LoginAs,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PRD-25 · TC-PRD-25a"""
    optiplex = make_product(make_product_type(name="Desktop"), "Optiplex", is_active=False)
    before = product_rows(db_session)
    login_as(client, make_user(role=role))

    response = client.post(f"/products/{optiplex.id}/activate")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert product_rows(db_session) == before
    assert product_rows(db_session)[0][3] is False
