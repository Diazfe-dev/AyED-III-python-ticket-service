import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import DuplicateProductTypeError
from app.domain.products import Category, ProductType
from app.repositories.product_type_repository import SqlAlchemyProductTypeRepository
from tests.conftest import MakeCategory


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_added_product_type_keeps_its_category(
    app: Flask, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-03 · TC-PTY-03c"""
    hardware = make_category("Hardware")
    product_type = ProductType(name="Notebook", category=hardware)
    SqlAlchemyProductTypeRepository(db_session).add(product_type)
    db_session.commit()

    with new_session(app) as other_session:
        found = SqlAlchemyProductTypeRepository(other_session).get(product_type.id)

        assert found is not None
        assert found.category_id == hardware.id
        assert found.category.name == "Hardware"


def test_adding_a_duplicate_name_in_the_category_raises_domain_error(
    db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-05 · TC-PTY-05c"""
    hardware = make_category("Hardware")
    repository = SqlAlchemyProductTypeRepository(db_session)
    repository.add(ProductType(name="Notebook", category=hardware))

    with pytest.raises(DuplicateProductTypeError):
        repository.add(ProductType(name="notebook", category=hardware))


def test_find_by_name_in_category_only_looks_inside_that_category(
    db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-05 · TC-PTY-05d"""
    hardware, office = make_category("Hardware"), make_category("Oficina")
    repository = SqlAlchemyProductTypeRepository(db_session)
    in_hardware = ProductType(name="Notebook", category=hardware)
    repository.add(in_hardware)
    repository.add(ProductType(name="Notebook", category=office))
    db_session.commit()

    assert repository.find_by_name_in_category(" NOTEBOOK ", hardware.id) is in_hardware


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
    """SPEC-PTY-06 · TC-PTY-06g"""
    assert SqlAlchemyProductTypeRepository(db_session).get(2**63) is None
