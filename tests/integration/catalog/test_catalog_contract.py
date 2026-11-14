import json
from pathlib import Path
from typing import Any

CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "openapi.json"
PRODUCT_TYPE_SCHEMAS = ("ProductType", "CreateProductTypeRequest", "UpdateProductTypeRequest")


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_exposes_no_category_paths_or_fields() -> None:
    """SPEC-PTY-35 · TC-PTY-35f"""
    contract = load_contract()
    components = contract["components"]

    assert [path for path in contract["paths"] if path.startswith("/categories")] == []
    for section in ("schemas", "responses", "parameters"):
        names = [name for name in components[section] if name.startswith("Category")]
        assert names == []
    for name in PRODUCT_TYPE_SCHEMAS:
        assert "category_id" not in components["schemas"][name]["properties"]
    listing_parameters = contract["paths"]["/product-types"]["get"]["parameters"]
    assert [parameter.get("name") for parameter in listing_parameters] == [None]
    assert "category" not in components["schemas"]["Product"]["properties"]
    product_parameters = contract["paths"]["/products"]["get"]["parameters"]
    assert "category_id" not in [parameter.get("name") for parameter in product_parameters]
