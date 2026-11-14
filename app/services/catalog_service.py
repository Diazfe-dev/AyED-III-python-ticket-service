"""Catalog use cases: categories and product types, their changes and listings."""

from collections.abc import Callable
from typing import Any, Protocol

from app.domain.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateProductTypeError,
    ProductTypeInUseError,
    ProductTypeNotFoundError,
)
from app.domain.products import Category, ProductType
from app.services.listing import search_text
from app.services.validation import raise_if_invalid, text_error


class CategoryRepository(Protocol):
    def add(self, category: Category) -> None: ...

    def get(self, category_id: int) -> Category | None: ...

    def find_by_name(self, name: str) -> Category | None: ...

    def list_all(self, q: str | None = None) -> list[Category]: ...

    def has_product_types(self, category_id: int) -> bool: ...

    def delete(self, category: Category) -> None: ...


class ProductTypeRepository(Protocol):
    def add(self, product_type: ProductType) -> None: ...

    def get(self, product_type_id: int) -> ProductType | None: ...

    def find_by_name(self, name: str) -> ProductType | None: ...

    def has_products(self, product_type_id: int) -> bool: ...

    def list_all(self, q: str | None = None) -> list[ProductType]: ...

    def delete(self, product_type: ProductType) -> None: ...


class CatalogService:
    def __init__(
        self,
        categories: CategoryRepository,
        product_types: ProductTypeRepository,
        commit: Callable[[], None],
    ) -> None:
        self._categories = categories
        self._product_types = product_types
        self._commit = commit

    def create_category(self, name: Any) -> Category:
        """Create a category; input comes unchecked from the caller and is validated here."""
        raise_if_invalid({"name": text_error(name)})
        self._ensure_category_name_is_free(name)
        category = Category(name=name)
        self._categories.add(category)
        self._commit()
        return category

    def update_category(self, category_id: int, *, name: Any = None) -> Category:
        """Rename a category; a name left as `None` keeps the current one."""
        category = self._get_category(category_id)
        if name is not None:
            raise_if_invalid({"name": text_error(name)})
            self._ensure_category_name_is_free(name, owner=category)
            category.name = name
        self._commit()
        return category

    def delete_category(self, category_id: int) -> None:
        """Physical deletion of a category that has no product types."""
        category = self._get_category(category_id)
        if self._categories.has_product_types(category.id):
            raise CategoryInUseError()
        self._categories.delete(category)
        self._commit()

    def list_categories(self, q: str | None = None) -> list[Category]:
        """Every category ordered by name without case; with `q`, only names containing it."""
        return self._categories.list_all(q=search_text(q))

    def create_product_type(self, name: Any) -> ProductType:
        """Create a product type; its name is unique in the whole catalog."""
        raise_if_invalid({"name": text_error(name)})
        if self._product_types.find_by_name(name) is not None:
            raise DuplicateProductTypeError()
        product_type = ProductType(name=name)
        self._product_types.add(product_type)
        self._commit()
        return product_type

    def update_product_type(self, product_type_id: int, *, name: Any = None) -> ProductType:
        """Rename a product type; a name left as `None` keeps the current one."""
        product_type = self._get_product_type(product_type_id)
        if name is not None:
            raise_if_invalid({"name": text_error(name)})
            holder = self._product_types.find_by_name(name)
            if holder is not None and holder is not product_type:
                raise DuplicateProductTypeError()
            product_type.name = name
        self._commit()
        return product_type

    def delete_product_type(self, product_type_id: int) -> None:
        """Physical deletion of a product type that has no products, active or inactive."""
        product_type = self._get_product_type(product_type_id)
        if self._product_types.has_products(product_type.id):
            raise ProductTypeInUseError()
        self._product_types.delete(product_type)
        self._commit()

    def list_product_types(self, q: str | None = None) -> list[ProductType]:
        """Every product type ordered by name without case; with `q`, only names containing it."""
        return self._product_types.list_all(q=search_text(q))

    def _get_product_type(self, product_type_id: int) -> ProductType:
        product_type = self._product_types.get(product_type_id)
        if product_type is None:
            raise ProductTypeNotFoundError()
        return product_type

    def _get_category(self, category_id: int) -> Category:
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError()
        return category

    def _ensure_category_name_is_free(self, name: str, owner: Category | None = None) -> None:
        holder = self._categories.find_by_name(name)
        if holder is not None and holder is not owner:
            raise DuplicateCategoryError()
