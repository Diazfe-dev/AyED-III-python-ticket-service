"""Persistence of product types on top of the SQLAlchemy session."""

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import fits_integer_column
from app.domain.errors import DuplicateProductTypeError, ProductTypeInUseError
from app.domain.products import Category, Product, ProductType, normalize_name


class SqlAlchemyProductTypeRepository:
    """Stores, finds and deletes product types; it never commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, product_type: ProductType) -> None:
        """Stage the type and flush, so a UNIQUE violation surfaces here and not at commit."""
        self._session.add(product_type)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise DuplicateProductTypeError() from error

    def get(self, product_type_id: int) -> ProductType | None:
        """The product type, or `None`; an id SQLite cannot store matches nothing."""
        if not fits_integer_column(product_type_id):
            return None
        return self._session.get(ProductType, product_type_id)

    def find_by_name_in_category(self, name: str, category_id: int) -> ProductType | None:
        statement = select(ProductType).where(
            ProductType.category_id == category_id,
            ProductType.name_key == normalize_name(name),
        )
        return self._session.scalars(statement).one_or_none()

    def has_products(self, product_type_id: int) -> bool:
        """Whether any product, active or inactive, belongs to the type."""
        statement = select(exists().where(Product.product_type_id == product_type_id))
        return bool(self._session.scalar(statement))

    def delete(self, product_type: ProductType) -> None:
        """Delete and flush; the foreign key rejects a product type that still has products."""
        self._session.delete(product_type)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise ProductTypeInUseError() from error

    def search(self, q: str, category_id: int | None = None) -> list[ProductType]:
        """Types whose name contains `q` ignoring case, with their category loaded.

        `%` and `_` in `q` are literal. Ordered by category name and id, then type name and id.
        """
        statement = (
            select(ProductType)
            .join(ProductType.category)
            .where(ProductType.name_key.contains(q.casefold(), autoescape=True))
            .options(selectinload(ProductType.category))
            .order_by(Category.name_key, Category.id, ProductType.name_key, ProductType.id)
        )
        if category_id is not None:
            statement = statement.where(ProductType.category_id == category_id)
        return list(self._session.scalars(statement).all())
