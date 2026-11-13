"""Product use cases: creation, changes, logical deactivation and listings."""

from collections.abc import Callable
from typing import Any, Protocol

from app.domain.errors import (
    CategoryNotFoundError,
    DuplicateProductError,
    ProductNotFoundError,
    ProductTypeNotFoundError,
)
from app.domain.products import Category, Product, ProductType
from app.services.catalog_service import CategoryRepository, ProductTypeRepository
from app.services.validation import id_error, parse_id, provided, raise_if_invalid, text_error


class ProductRepository(Protocol):
    def add(self, product: Product) -> None: ...

    def get(self, product_id: int) -> Product | None: ...

    def find_by_name_in_type(self, name: str, product_type_id: int) -> Product | None: ...

    def list_matching(
        self,
        category_id: int | None = None,
        product_type_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[Product]: ...


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        product_types: ProductTypeRepository,
        categories: CategoryRepository,
        commit: Callable[[], None],
    ) -> None:
        self._products = products
        self._product_types = product_types
        self._categories = categories
        self._commit = commit

    def create_product(self, name: Any, product_type_id: Any) -> Product:
        """Create an active product of an existing type; input is validated here."""
        raise_if_invalid({"name": text_error(name), "product_type_id": id_error(product_type_id)})
        product_type = self._get_product_type(parse_id(product_type_id))
        self._ensure_name_is_free(name, product_type)
        product = Product(name=name, product_type=product_type, is_active=True)
        self._products.add(product)
        self._commit()
        return product

    def update_product(
        self, product_id: int, *, name: Any = None, product_type_id: Any = None
    ) -> Product:
        """Rename or move a product, active or not; a field left as `None` keeps its value."""
        product = self._get_product(product_id)
        changes = provided(name=name, product_type_id=product_type_id)
        raise_if_invalid({field: PRODUCT_FIELDS[field](value) for field, value in changes.items()})
        new_name = changes.get("name", product.name)
        product_type = product.product_type
        if "product_type_id" in changes:
            product_type = self._get_product_type(parse_id(product_type_id))
        self._ensure_name_is_free(new_name, product_type, owner=product)
        product.name = new_name
        product.product_type = product_type
        self._commit()
        return product

    def deactivate_product(self, product_id: int) -> Product:
        """Logical deletion: the product stays stored; an inactive one is left as it is."""
        product = self._get_product(product_id)
        product.deactivate()
        self._commit()
        return product

    def list_products(self, category_id: Any = None, product_type_id: Any = None) -> list[Product]:
        """Products, active and inactive, matching every filter given.

        Filters come as query string text: both are validated together, then each must exist.
        """
        filters = provided(category_id=category_id, product_type_id=product_type_id)
        raise_if_invalid({field: id_error(value) for field, value in filters.items()})
        ids = {field: parse_id(value) for field, value in filters.items()}
        if "category_id" in ids:
            self._get_category(ids["category_id"])
        if "product_type_id" in ids:
            self._get_product_type(ids["product_type_id"])
        return self._products.list_matching(**ids)

    def list_available_products(self) -> list[Product]:
        """Active products: the ones that can be added to a ticket."""
        return self._products.list_matching(is_active=True)

    def _get_product(self, product_id: int) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise ProductNotFoundError()
        return product

    def _get_category(self, category_id: int) -> Category:
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError()
        return category

    def _get_product_type(self, product_type_id: int) -> ProductType:
        product_type = self._product_types.get(product_type_id)
        if product_type is None:
            raise ProductTypeNotFoundError()
        return product_type

    def _ensure_name_is_free(
        self, name: str, product_type: ProductType, owner: Product | None = None
    ) -> None:
        holder = self._products.find_by_name_in_type(name, product_type.id)
        if holder is not None and holder is not owner:
            raise DuplicateProductError()


PRODUCT_FIELDS: dict[str, Callable[[Any], str | None]] = {
    "name": text_error,
    "product_type_id": id_error,
}
