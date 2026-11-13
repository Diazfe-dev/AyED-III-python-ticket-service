"""Persistence of products on top of the SQLAlchemy session."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import fits_integer_column
from app.domain.errors import DuplicateProductError
from app.domain.products import Product, ProductType, normalize_name

BY_NAME = (Product.name_key, Product.id)
WITH_TYPE_AND_CATEGORY = selectinload(Product.product_type).selectinload(ProductType.category)


class SqlAlchemyProductRepository:
    """Stores, finds and lists products; it never commits and never deletes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, product: Product) -> None:
        """Stage the product and flush, so a UNIQUE violation surfaces here and not at commit."""
        self._session.add(product)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise DuplicateProductError() from error

    def get(self, product_id: int) -> Product | None:
        """The product, or `None`; an id SQLite cannot store matches nothing."""
        if not fits_integer_column(product_id):
            return None
        return self._session.get(Product, product_id)

    def get_many(self, product_ids: list[int]) -> list[Product]:
        """The existing products among the ids, active or not, by id and without duplicates.

        Ids SQLite cannot store match nothing; when no id is left, nothing is queried.
        """
        wanted = {pid for pid in product_ids if fits_integer_column(pid)}
        if not wanted:
            return []
        statement = (
            select(Product)
            .options(WITH_TYPE_AND_CATEGORY)
            .where(Product.id.in_(wanted))
            .order_by(Product.id)
        )
        return list(self._session.scalars(statement))

    def find_by_name_in_type(self, name: str, product_type_id: int) -> Product | None:
        statement = select(Product).where(
            Product.product_type_id == product_type_id,
            Product.name_key == normalize_name(name),
        )
        return self._session.scalars(statement).one_or_none()

    def list_matching(
        self,
        category_id: int | None = None,
        product_type_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[Product]:
        """Products matching every given filter, ordered by name without case.

        The category of a product is the one of its type, so that filter joins the type.
        """
        statement = select(Product).options(WITH_TYPE_AND_CATEGORY).order_by(*BY_NAME)
        if category_id is not None:
            statement = statement.join(Product.product_type).where(
                ProductType.category_id == category_id
            )
        if product_type_id is not None:
            statement = statement.where(Product.product_type_id == product_type_id)
        if is_active is not None:
            statement = statement.where(Product.is_active == is_active)
        return list(self._session.scalars(statement))
