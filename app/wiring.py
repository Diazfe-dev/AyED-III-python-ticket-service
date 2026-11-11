"""Builds the services of the current request, so controllers never touch the session."""

from datetime import UTC, datetime

from app.db import get_session
from app.repositories.category_repository import SqlAlchemyCategoryRepository
from app.repositories.product_repository import SqlAlchemyProductRepository
from app.repositories.product_type_repository import SqlAlchemyProductTypeRepository
from app.repositories.ticket_repository import SqlAlchemyTicketRepository
from app.repositories.user_repository import SqlAlchemyUserRepository
from app.services.catalog_service import CatalogService
from app.services.product_service import ProductService
from app.services.ticket_service import NullTicketNotifier, TicketService


def get_catalog_service() -> CatalogService:
    db_session = get_session()
    return CatalogService(
        SqlAlchemyCategoryRepository(db_session),
        SqlAlchemyProductTypeRepository(db_session),
        db_session.commit,
    )


def get_product_service() -> ProductService:
    db_session = get_session()
    return ProductService(
        SqlAlchemyProductRepository(db_session),
        SqlAlchemyProductTypeRepository(db_session),
        SqlAlchemyCategoryRepository(db_session),
        db_session.commit,
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_ticket_service() -> TicketService:
    db_session = get_session()
    return TicketService(
        SqlAlchemyTicketRepository(db_session),
        SqlAlchemyUserRepository(db_session),
        SqlAlchemyProductRepository(db_session),
        utc_now,
        db_session.commit,
        NullTicketNotifier(),
    )
