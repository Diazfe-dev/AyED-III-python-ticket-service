from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Category, ProductType
from tests.conftest import LoginAs, MakeCategory, MakeProductType, MakeUser

# (method, path, body); `{category}`, `{empty}` and `{type}` are ids of the `catalog` fixture.
WRITE_ENDPOINTS = [
    ("POST", "/categories", {"name": "Redes"}),
    ("PATCH", "/categories/{category}", {"name": "Redes"}),
    ("DELETE", "/categories/{empty}", None),
    ("POST", "/product-types", {"name": "Router", "category_id": "{category}"}),
    ("PATCH", "/product-types/{type}", {"name": "Ultrabook"}),
    ("DELETE", "/product-types/{type}", None),
]

Snapshot = tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]


@pytest.fixture
def catalog(make_category: MakeCategory, make_product_type: MakeProductType) -> dict[str, int]:
    """`Hardware` with the type `Notebook`, and the empty category `Oficina`."""
    hardware, office = make_category("Hardware"), make_category("Oficina")
    notebook = make_product_type(hardware, "Notebook")
    return {"category": hardware.id, "empty": office.id, "type": notebook.id}


def snapshot(db_session: Session) -> Snapshot:
    db_session.expire_all()
    categories = db_session.execute(select(Category.id, Category.name).order_by(Category.id))
    types = db_session.execute(
        select(ProductType.id, ProductType.name, ProductType.category_id).order_by(ProductType.id)
    )
    return [tuple(row) for row in categories], [tuple(row) for row in types]


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
    if isinstance(body, dict) and body.get("category_id") == "{category}":
        body = body | {"category_id": catalog["category"]}
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
    """SPEC-PTY-11 · TC-PTY-11a"""
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
    """SPEC-PTY-11 · TC-PTY-11b"""
    before = snapshot(db_session)

    response = call_as("Client", endpoint, catalog, client, make_user, login_as)

    assert response.status_code == 403
    assert snapshot(db_session) == before
