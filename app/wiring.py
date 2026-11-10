"""Builds the services of the current request, so controllers never touch the session."""

from app.db import get_session
from app.repositories.category_repository import SqlAlchemyCategoryRepository
from app.repositories.product_type_repository import SqlAlchemyProductTypeRepository
from app.services.catalog_service import CatalogService


def get_catalog_service() -> CatalogService:
    db_session = get_session()
    return CatalogService(
        SqlAlchemyCategoryRepository(db_session),
        SqlAlchemyProductTypeRepository(db_session),
        db_session.commit,
    )
