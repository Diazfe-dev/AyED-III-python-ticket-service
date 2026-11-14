from app.domain.products import Product, ProductType, normalize_name


def test_normalize_name_trims_and_casefolds_non_ascii_letters() -> None:
    """SPEC-PTY-26 · TC-PTY-26e"""
    assert normalize_name("  Hardware ") == "hardware"
    assert normalize_name("ÁUDIO") == "áudio"


def test_product_type_has_trimmed_name_and_normalized_key() -> None:
    """SPEC-PTY-25 · TC-PTY-25b"""
    product_type = ProductType(name=" Notebook ")

    assert product_type.name == "Notebook"
    assert product_type.name_key == "notebook"


def test_product_type_name_is_trimmed_on_every_assignment() -> None:
    """SPEC-PTY-28 · TC-PTY-28a"""
    product_type = ProductType(name=" Notebook ")

    product_type.name = "  Ultrabook "

    assert product_type.name == "Ultrabook"
    assert product_type.name_key == "ultrabook"


def notebook_type() -> ProductType:
    return ProductType(name="Notebook")


def test_product_belongs_to_its_product_type() -> None:
    """SPEC-PRD-01 · TC-PRD-01a"""
    notebook = notebook_type()

    product = Product(name="XPS 13", product_type=notebook, is_active=True)

    assert product.product_type is notebook
    assert product in notebook.products


def test_deactivated_product_is_inactive() -> None:
    """SPEC-PRD-05 · TC-PRD-05a"""
    product = Product(name="XPS 13", product_type=notebook_type(), is_active=True)

    product.deactivate()

    assert product.is_active is False


def test_activated_product_is_active() -> None:
    """SPEC-PRD-22 · TC-PRD-22a"""
    product = Product(name="XPS 13", product_type=notebook_type(), is_active=False)

    product.activate()

    assert product.is_active is True


def test_product_name_is_trimmed_on_every_assignment() -> None:
    """SPEC-PRD-14 · TC-PRD-14a"""
    product = Product(name="  XPS  13 ", product_type=notebook_type())

    assert product.name == "XPS  13"
    assert product.name_key == "xps  13"

    product.name = " XPS 15 "

    assert product.name == "XPS 15"
    assert product.name_key == "xps 15"
