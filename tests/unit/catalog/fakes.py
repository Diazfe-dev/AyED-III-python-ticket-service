"""In-memory test doubles for the catalog service: no Flask, no database."""

from app.domain.paging import Page, PageRequest
from app.domain.products import Product, ProductType, normalize_name


def _by_name(entity: ProductType | Product) -> tuple[str, int]:
    return entity.name_key, entity.id


class FakeProductTypeRepository:
    """Dictionary-backed repository."""

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

    def find_by_name(self, name: str) -> ProductType | None:
        wanted = normalize_name(name)
        found = (t for t in self.product_types.values() if t.name_key == wanted)
        return next(found, None)

    def has_products(self, product_type_id: int) -> bool:
        return bool(self.product_types[product_type_id].products)

    def list_all(self, q: str | None = None) -> list[ProductType]:
        wanted = "" if q is None else q.casefold()
        found = (t for t in self.product_types.values() if wanted in t.name_key)
        return sorted(found, key=_by_name)

    def delete(self, product_type: ProductType) -> None:
        del self.product_types[product_type.id]


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
        product_type_id: int | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        window: PageRequest | None = None,
    ) -> list[Product] | Page[Product]:
        wanted = "" if q is None else q.casefold()
        matching = [
            p
            for p in self.products.values()
            if product_type_id in (None, p.product_type.id)
            and is_active in (None, p.is_active)
            and wanted in p.name_key
        ]
        ordered = sorted(matching, key=_by_name)
        if window is None:
            return ordered
        items = ordered[window.offset : window.offset + window.limit]
        return Page(items=items, page=window.page, page_size=window.page_size, total=len(ordered))
