"""Product catalog: product types (the trade, or rubro) and the products of each type."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.base import Base

NAME_LENGTH = 120


def normalize_name(name: str) -> str:
    """Comparison key of a catalog name: no surrounding spaces and case-folded."""
    return name.strip().casefold()


class CatalogName:
    """A display name stored trimmed, plus the `name_key` used to compare names."""

    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    name_key: Mapped[str] = mapped_column(String(NAME_LENGTH))

    @validates("name")
    def _store_name(self, _key: str, name: str) -> str:
        self.name_key = normalize_name(name)
        return name.strip()


class ProductType(CatalogName, Base):
    """A kind of product: the trade (rubro) that technicians specialize in."""

    __tablename__ = "product_types"
    __table_args__ = (UniqueConstraint("name_key", name="uq_product_types_name_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    products: Mapped[list["Product"]] = relationship(
        back_populates="product_type", passive_deletes="all"
    )


class Product(CatalogName, Base):
    """A product of one product type; it is deactivated, never deleted."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_type_id", "name_key", name="uq_products_type_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_type_id: Mapped[int] = mapped_column(
        ForeignKey("product_types.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    product_type: Mapped[ProductType] = relationship(back_populates="products")

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
