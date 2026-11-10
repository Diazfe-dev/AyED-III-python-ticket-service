"""Catalog use cases: categories and product types, their changes and listings."""

from collections.abc import Callable
from typing import Any, Protocol

from app.domain.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateProductTypeError,
    ProductTypeNotFoundError,
)
from app.domain.products import Category, ProductType
from app.services.validation import id_error, parse_id, provided, raise_if_invalid, text_error


class CategoryRepository(Protocol):
    def add(self, category: Category) -> None: ...

    def get(self, category_id: int) -> Category | None: ...

    def find_by_name(self, name: str) -> Category | None: ...

    def list_all(self) -> list[Category]: ...

    def list_with_product_types(self) -> list[Category]: ...

    def has_product_types(self, category_id: int) -> bool: ...

    def delete(self, category: Category) -> None: ...


class ProductTypeRepository(Protocol):
    def add(self, product_type: ProductType) -> None: ...

    def get(self, product_type_id: int) -> ProductType | None: ...

    def find_by_name_in_category(self, name: str, category_id: int) -> ProductType | None: ...

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

    def list_categories(self) -> list[Category]:
        """Every category, ordered by name without case."""
        return self._categories.list_all()

    def create_product_type(self, name: Any, category_id: Any) -> ProductType:
        """Create a product type in an existing category, with a name unique inside it."""
        raise_if_invalid({"name": text_error(name), "category_id": id_error(category_id)})
        category = self._get_category(parse_id(category_id))
        self._ensure_type_name_is_free(name, category)
        product_type = ProductType(name=name, category=category)
        self._product_types.add(product_type)
        self._commit()
        return product_type

    def update_product_type(
        self, product_type_id: int, *, name: Any = None, category_id: Any = None
    ) -> ProductType:
        """Rename or move a product type; a field left as `None` keeps its value."""
        product_type = self._get_product_type(product_type_id)
        changes = provided(name=name, category_id=category_id)
        raise_if_invalid({field: TYPE_FIELDS[field](value) for field, value in changes.items()})
        new_name = changes.get("name", product_type.name)
        category = product_type.category
        if "category_id" in changes:
            category = self._get_category(parse_id(category_id))
        self._ensure_type_name_is_free(new_name, category, owner=product_type)
        product_type.name = new_name
        product_type.category = category
        self._commit()
        return product_type

    def delete_product_type(self, product_type_id: int) -> None:
        """Physical deletion of a product type."""
        self._product_types.delete(self._get_product_type(product_type_id))
        self._commit()

    def list_product_types(self, category_id: Any = None) -> list[Category]:
        """Product types grouped by category: every category, or only the requested one."""
        if category_id is None:
            return self._categories.list_with_product_types()
        raise_if_invalid({"category_id": id_error(category_id)})
        return [self._get_category(parse_id(category_id))]

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

    def _ensure_type_name_is_free(
        self, name: str, category: Category, owner: ProductType | None = None
    ) -> None:
        holder = self._product_types.find_by_name_in_category(name, category.id)
        if holder is not None and holder is not owner:
            raise DuplicateProductTypeError()


TYPE_FIELDS: dict[str, Callable[[Any], str | None]] = {"name": text_error, "category_id": id_error}
