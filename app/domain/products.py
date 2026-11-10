"""Product catalog classification: categories and their product types."""

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


class Category(CatalogName, Base):
    """A category (rubro) that groups product types."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name_key", name="uq_categories_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_types: Mapped[list["ProductType"]] = relationship(
        back_populates="category",
        order_by="(ProductType.name_key, ProductType.id)",
        passive_deletes="all",
    )


class ProductType(CatalogName, Base):
    """A kind of product, classified under exactly one category."""

    __tablename__ = "product_types"
    __table_args__ = (
        UniqueConstraint("category_id", "name_key", name="uq_product_types_category_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    category: Mapped[Category] = relationship(back_populates="product_types")
