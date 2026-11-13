"""In-memory test doubles for the catalog service: no Flask, no database."""

from app.domain.products import Category, Product, ProductType, normalize_name


def _by_name(entity: Category | ProductType | Product) -> tuple[str, int]:
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

    def list_all(self, q: str | None = None) -> list[Category]:
        wanted = "" if q is None else q.casefold()
        found = (c for c in self.categories.values() if wanted in c.name_key)
        return sorted(found, key=_by_name)

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

    def has_products(self, product_type_id: int) -> bool:
        return bool(self.product_types[product_type_id].products)

    def search(self, q: str, category_id: int | None = None) -> list[ProductType]:
        wanted = q.casefold()
        found = [
            t
            for t in self.product_types.values()
            if wanted in t.name_key and category_id in (None, t.category.id)
        ]
        return sorted(found, key=lambda t: (*_by_name(t.category), *_by_name(t)))

    def delete(self, product_type: ProductType) -> None:
        del self.product_types[product_type.id]
        product_type.category.product_types.remove(product_type)


class FakeProductRepository:
    """Dictionary-backed repository; `back_populates` keeps `ProductType.products` in sync."""

    def __init__(self) -> None:
        self.products: dict[int, Product] = {}
        self._next_id = 1

    def add(self, product: Product) -> None:
        if product.id is None:
            product.id = self._next_id
            self._next_id += 1
        self.products[product.id] = product

    def get(self, product_id: int) -> Product | None:
        return self.products.get(product_id)

    def get_many(self, product_ids: list[int]) -> list[Product]:
        found = {pid: self.products[pid] for pid in product_ids if pid in self.products}
        return [found[pid] for pid in sorted(found)]

    def find_by_name_in_type(self, name: str, product_type_id: int) -> Product | None:
        wanted = normalize_name(name)
        found = (
            p
            for p in self.products.values()
            if p.product_type.id == product_type_id and p.name_key == wanted
        )
        return next(found, None)

    def list_matching(
        self,
        category_id: int | None = None,
        product_type_id: int | None = None,
        active_only: bool = False,
    ) -> list[Product]:
        matching = [
            p
            for p in self.products.values()
            if category_id in (None, p.product_type.category.id)
            and product_type_id in (None, p.product_type.id)
            and (p.is_active or not active_only)
        ]
        return sorted(matching, key=_by_name)
