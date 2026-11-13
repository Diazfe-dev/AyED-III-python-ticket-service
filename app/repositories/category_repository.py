"""Persistence of categories on top of the SQLAlchemy session."""

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import fits_integer_column
from app.domain.errors import CategoryInUseError, DuplicateCategoryError
from app.domain.products import Category, ProductType, normalize_name

BY_NAME = (Category.name_key, Category.id)


class SqlAlchemyCategoryRepository:
    """Stores, finds and deletes categories; it never commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, category: Category) -> None:
        """Stage the category and flush, so a UNIQUE violation surfaces here and not at commit."""
        self._session.add(category)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise DuplicateCategoryError() from error

    def get(self, category_id: int) -> Category | None:
        """The category, or `None`; an id SQLite cannot store matches nothing."""
        if not fits_integer_column(category_id):
            return None
        return self._session.get(Category, category_id)

    def find_by_name(self, name: str) -> Category | None:
        statement = select(Category).where(Category.name_key == normalize_name(name))
        return self._session.scalars(statement).one_or_none()

    def list_all(self, q: str | None = None) -> list[Category]:
        """Every category ordered by name without case; with `q`, only names containing it.

        The match ignores case and `%` and `_` in `q` are literal.
        """
        statement = select(Category)
        if q is not None:
            statement = statement.where(Category.name_key.contains(q.casefold(), autoescape=True))
        return list(self._session.scalars(statement.order_by(*BY_NAME)))

    def list_with_product_types(self) -> list[Category]:
        """Every category, empty ones included, with its product types loaded in one query."""
        statement = select(Category).options(selectinload(Category.product_types))
        return list(self._session.scalars(statement.order_by(*BY_NAME)))

    def has_product_types(self, category_id: int) -> bool:
        statement = select(exists().where(ProductType.category_id == category_id))
        return bool(self._session.scalar(statement))

    def delete(self, category: Category) -> None:
        """Delete and flush; the foreign key rejects a category that still has product types."""
        self._session.delete(category)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise CategoryInUseError() from error
