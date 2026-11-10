from app.domain.products import Category, Product, ProductType, normalize_name


def test_normalize_name_trims_and_casefolds_non_ascii_letters() -> None:
    """SPEC-PTY-02 · TC-PTY-02a"""
    assert normalize_name("  Hardware ") == "hardware"
    assert normalize_name("ÁUDIO") == "áudio"


def test_category_keeps_trimmed_name_and_normalized_key() -> None:
    """SPEC-PTY-02 · TC-PTY-02b"""
    category = Category(name="  Hardware ")

    assert category.name == "Hardware"
    assert category.name_key == "hardware"


def test_category_name_keeps_inner_spaces() -> None:
    """SPEC-PTY-19 · TC-PTY-19a"""
    category = Category(name="  Mesa de  ayuda ")

    assert category.name == "Mesa de  ayuda"


def test_product_type_belongs_to_its_category_with_trimmed_name() -> None:
    """SPEC-PTY-03 · TC-PTY-03b"""
    hardware = Category(name="Hardware")

    product_type = ProductType(name=" Notebook ", category=hardware)

    assert product_type.name == "Notebook"
    assert product_type.name_key == "notebook"
    assert product_type in hardware.product_types


def test_product_type_name_is_trimmed_on_every_assignment() -> None:
    """SPEC-PTY-19 · TC-PTY-19b"""
    product_type = ProductType(name=" Notebook ", category=Category(name="Hardware"))

    product_type.name = "  Ultrabook "

    assert product_type.name == "Ultrabook"
    assert product_type.name_key == "ultrabook"


def notebook_type() -> ProductType:
    return ProductType(name="Notebook", category=Category(name="Hardware"))


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


def test_product_name_is_trimmed_on_every_assignment() -> None:
    """SPEC-PRD-14 · TC-PRD-14a"""
    product = Product(name="  XPS  13 ", product_type=notebook_type())

    assert product.name == "XPS  13"
    assert product.name_key == "xps  13"

    product.name = " XPS 15 "

    assert product.name == "XPS 15"
    assert product.name_key == "xps 15"
