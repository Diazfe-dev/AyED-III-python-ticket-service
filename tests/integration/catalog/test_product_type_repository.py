import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import DuplicateProductTypeError, ProductTypeInUseError
from app.domain.products import Category, Product, ProductType
from app.repositories.product_type_repository import SqlAlchemyProductTypeRepository
from tests.conftest import MakeCategory, MakeProduct, MakeProductType
from tests.integration.catalog.queries import count_statements


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_added_product_type_without_category_is_stored(app: Flask, db_session: Session) -> None:
    """SPEC-PTY-25 · TC-PTY-25c"""
    product_type = ProductType(name="Notebook")
    SqlAlchemyProductTypeRepository(db_session).add(product_type)
    db_session.commit()

    with new_session(app) as other_session:
        found = SqlAlchemyProductTypeRepository(other_session).get(product_type.id)

        assert found is not None
        assert found.name == "Notebook"


def test_find_by_name_looks_in_the_whole_catalog(db_session: Session) -> None:
    """SPEC-PTY-26 · TC-PTY-26b"""
    repository = SqlAlchemyProductTypeRepository(db_session)
    notebook = ProductType(name="Notebook")
    repository.add(notebook)

    assert repository.find_by_name(" notebook ") is notebook
    assert repository.find_by_name("Otro") is None


def test_adding_a_duplicate_name_raises_domain_error(db_session: Session) -> None:
    """SPEC-PTY-26 · TC-PTY-26c"""
    repository = SqlAlchemyProductTypeRepository(db_session)
    repository.add(ProductType(name="Notebook"))

    with pytest.raises(DuplicateProductTypeError):
        repository.add(ProductType(name="notebook"))


def test_names_are_compared_with_casefold_outside_ascii(db_session: Session) -> None:
    """SPEC-PTY-26 · TC-PTY-26f"""
    repository = SqlAlchemyProductTypeRepository(db_session)
    audio = ProductType(name="áudio")
    repository.add(audio)
    db_session.commit()

    with pytest.raises(DuplicateProductTypeError):
        repository.add(ProductType(name="ÁUDIO"))
    db_session.rollback()
    assert repository.find_by_name("ÁUDIO") is audio


def test_deleted_product_type_is_gone_and_its_category_stays(
    app: Flask, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-07 · TC-PTY-07c"""
    hardware = make_category("Hardware")
    repository = SqlAlchemyProductTypeRepository(db_session)
    product_type = ProductType(name="Notebook", category=hardware)
    repository.add(product_type)
    db_session.commit()

    repository.delete(product_type)
    db_session.commit()

    with new_session(app) as other_session:
        assert SqlAlchemyProductTypeRepository(other_session).get(product_type.id) is None
        assert other_session.get(Category, hardware.id) is not None


def test_get_with_an_id_beyond_sqlite_integers_finds_nothing(db_session: Session) -> None:
    """SPEC-PTY-29 · TC-PTY-29f"""
    assert SqlAlchemyProductTypeRepository(db_session).get(2**63) is None


def test_has_products_counts_inactive_products(
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08d"""
    hardware = make_category("Hardware")
    used, empty = make_product_type(hardware), make_product_type(hardware)
    make_product(used, is_active=False)
    repository = SqlAlchemyProductTypeRepository(db_session)

    assert repository.has_products(used.id) is True
    assert repository.has_products(empty.id) is False


def test_deleting_a_product_type_with_products_raises_in_use_and_keeps_both_rows(
    app: Flask,
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08b"""
    product_type = make_product_type(make_category("Hardware"))
    product = make_product(product_type)
    assert product_type.products == [product]

    with pytest.raises(ProductTypeInUseError) as raised:
        SqlAlchemyProductTypeRepository(db_session).delete(product_type)
    db_session.rollback()

    assert "FOREIGN KEY" in str(raised.value.__cause__)

    with new_session(app) as other_session:
        assert other_session.get(ProductType, product_type.id) is not None
        stored_product = other_session.get(Product, product.id)
        assert stored_product is not None
        assert stored_product.product_type_id == product_type.id


REFERENCE_NAMES = ["Router", "Notebook", "Ruteador USB", "Cámara", "50% off", "access point"]


def make_reference_types(
    make_category: MakeCategory, make_product_type: MakeProductType
) -> list[ProductType]:
    hardware = make_category("Hardware")
    return [make_product_type(hardware, name) for name in REFERENCE_NAMES]


def test_list_all_orders_by_name_in_a_single_statement(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-31 · TC-PTY-31b"""
    make_reference_types(make_category, make_product_type)
    db_session.expire_all()

    with count_statements(db_session) as statements:
        found = SqlAlchemyProductTypeRepository(db_session).list_all()

    assert [t.name for t in found] == [
        "50% off",
        "access point",
        "Cámara",
        "Notebook",
        "Router",
        "Ruteador USB",
    ]
    assert len(statements) == 1


def test_list_all_filters_by_name_ignoring_case_with_literal_wildcards(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-32 · TC-PTY-32b"""
    make_reference_types(make_category, make_product_type)
    repository = SqlAlchemyProductTypeRepository(db_session)

    assert [t.name for t in repository.list_all(q="CÁM")] == ["Cámara"]
    assert [t.name for t in repository.list_all(q="%")] == ["50% off"]
    assert [t.name for t in repository.list_all(q="_")] == []
