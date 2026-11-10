"""In-memory test doubles for the catalog service: no Flask, no database."""

from app.domain.products import Category, ProductType, normalize_name


def _by_name(entity: Category | ProductType) -> tuple[str, int]:
    return entity.name_key, entity.id


class FakeCategoryRepository:
    """Dictionary-backed repository that assigns ids like the database would."""

    def __init__(self) -> None:
        self.categories: dict[int, Category] = {}
        self._next_id = 1

    def add(self, category: Category) -> None:
        if category.id is None:
            category.id = self._next_id
            self._next_id += 1
        self.categories[category.id] = category

    def get(self, category_id: int) -> Category | None:
        return self.categories.get(category_id)

    def find_by_name(self, name: str) -> Category | None:
        wanted = normalize_name(name)
        found = (c for c in self.categories.values() if c.name_key == wanted)
        return next(found, None)

    def list_all(self) -> list[Category]:
        return sorted(self.categories.values(), key=_by_name)

    def list_with_product_types(self) -> list[Category]:
        categories = self.list_all()
        for category in categories:
            category.product_types.sort(key=_by_name)
        return categories

    def has_product_types(self, category_id: int) -> bool:
        return bool(self.categories[category_id].product_types)

    def delete(self, category: Category) -> None:
        del self.categories[category.id]


class FakeProductTypeRepository:
    """Dictionary-backed repository; `back_populates` keeps `Category.product_types` in sync."""

    def __init__(self) -> None:
        self.product_types: dict[int, ProductType] = {}
        self._next_id = 1

    def add(self, product_type: ProductType) -> None:
        if product_type.id is None:
            product_type.id = self._next_id
            self._next_id += 1
        self.product_types[product_type.id] = product_type

    def get(self, product_type_id: int) -> ProductType | None:
        return self.product_types.get(product_type_id)

    def find_by_name_in_category(self, name: str, category_id: int) -> ProductType | None:
        wanted = normalize_name(name)
        found = (
            t
            for t in self.product_types.values()
            if t.category.id == category_id and t.name_key == wanted
        )
        return next(found, None)

    def delete(self, product_type: ProductType) -> None:
        del self.product_types[product_type.id]
        product_type.category.product_types.remove(product_type)
