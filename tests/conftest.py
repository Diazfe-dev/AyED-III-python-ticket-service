import itertools
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from functools import cache

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session

from app import create_app
from app.auth import USER_ID_KEY
from app.db import EXTENSION_KEY, create_schema, get_engine
from app.domain.base import Base
from app.domain.products import Category, Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import ROLE_CLASSES, Client, Representative, User
from app.services.passwords import WerkzeugPasswordHasher

MakeUser = Callable[..., User]
MakeCategory = Callable[..., Category]
MakeProductType = Callable[..., ProductType]
MakeProduct = Callable[..., Product]
MakeTicket = Callable[..., Ticket]
LoginAs = Callable[[FlaskClient, User], None]


@pytest.fixture
def app() -> Iterator[Flask]:
    app = create_app({"TESTING": True})
    yield app
    with app.app_context():
        get_engine().dispose()


@pytest.fixture
def unpropagated_app() -> Iterator[Flask]:
    """A testing app that handles unhandled errors as in production instead of re-raising them."""
    app = create_app({"TESTING": True, "PROPAGATE_EXCEPTIONS": False})
    yield app
    with app.app_context():
        get_engine().dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    return app.test_cli_runner()


@pytest.fixture
def schema(app: Flask) -> None:
    """Create every domain table in the in-memory database of the test app."""
    with app.app_context():
        create_schema(get_engine(), Base.metadata)


@pytest.fixture
def db_session(app: Flask, schema: None) -> Iterator[Session]:
    """A session built straight from the factory, without holding an app context open.

    Holding an app context would make the test client reuse it, so every request would
    share this session and skip its own teardown.
    """
    session = app.extensions[EXTENSION_KEY]["session_factory"]()
    yield session
    session.close()


@cache
def _hash(password: str) -> str:
    """Hash each test password once: the real scrypt hash is slow."""
    return WerkzeugPasswordHasher().hash(password)


@pytest.fixture
def make_user(db_session: Session) -> MakeUser:
    """Persist and commit a user with a real hash; emails are unique unless given."""
    sequence = itertools.count(1)

    def make(
        role: str = "Client",
        email: str | None = None,
        password: str = "password1",
        is_active: bool = True,
        name: str = "Test User",
    ) -> User:
        user = ROLE_CLASSES[role](
            name=name,
            email=email or f"{role.lower()}{next(sequence)}@x.com",
            password_hash=_hash(password),
            preferred_channel="mail",
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        return user

    return make


def _login_as(client: FlaskClient, user: User) -> None:
    with client.session_transaction() as session:
        session[USER_ID_KEY] = user.id


@pytest.fixture
def login_as() -> LoginAs:
    """Store the user id in the client's session without going through POST /login."""
    return _login_as


@pytest.fixture
def admin(make_user: MakeUser) -> User:
    return make_user(role="Admin", email="admin@x.com")


@pytest.fixture
def admin_client(client: FlaskClient, admin: User) -> FlaskClient:
    _login_as(client, admin)
    return client


@pytest.fixture
def make_category(db_session: Session) -> MakeCategory:
    """Persist and commit a category; names are unique unless given."""
    sequence = itertools.count(1)

    def make(name: str | None = None) -> Category:
        category = Category(name=name or f"Category {next(sequence)}")
        db_session.add(category)
        db_session.commit()
        return category

    return make


@pytest.fixture
def make_product_type(db_session: Session) -> MakeProductType:
    """Persist and commit a product type of the category; names are unique unless given."""
    sequence = itertools.count(1)

    def make(category: Category, name: str | None = None) -> ProductType:
        product_type = ProductType(name=name or f"Type {next(sequence)}", category=category)
        db_session.add(product_type)
        db_session.commit()
        return product_type

    return make


@pytest.fixture
def make_product(db_session: Session) -> MakeProduct:
    """Persist and commit a product of the type; names are unique unless given."""
    sequence = itertools.count(1)

    def make(product_type: ProductType, name: str | None = None, is_active: bool = True) -> Product:
        product = Product(
            name=name or f"Product {next(sequence)}",
            product_type=product_type,
            is_active=is_active,
        )
        db_session.add(product)
        db_session.commit()
        return product

    return make


DEFAULT_TICKET_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_ticket(db_session: Session) -> MakeTicket:
    """Persist and commit a ticket opened with `Ticket.open`; without `now`, a fixed UTC date."""

    def make(
        client: Client,
        representative: Representative,
        products: Iterable[Product] = (),
        first_message: str = "Hola",
        now: datetime | None = None,
    ) -> Ticket:
        ticket = Ticket.open(
            client, representative, products, first_message, now or DEFAULT_TICKET_TIME
        )
        db_session.add(ticket)
        db_session.commit()
        return ticket

    return make
