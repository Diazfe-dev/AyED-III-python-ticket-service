import re

from flask import Flask
from flask.testing import FlaskClient

IGNORED_METHODS = {"HEAD", "OPTIONS"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
FLASK_PARAM = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")

Route = tuple[str, str]


def test_openapi_contract_is_served_as_openapi_3_1_json(client: FlaskClient) -> None:
    """SPEC-PLT-12 · TC-PLT-12a"""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json()["openapi"].startswith("3.1")


def test_openapi_contract_does_not_require_authentication(client: FlaskClient) -> None:
    """SPEC-PLT-12 · TC-PLT-12b"""
    response = client.get("/openapi.json", follow_redirects=False)

    assert response.status_code == 200


def test_docs_page_renders_swagger_ui_for_the_contract(client: FlaskClient) -> None:
    """SPEC-PLT-13 · TC-PLT-13a"""
    response = client.get("/docs", follow_redirects=False)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert '"/openapi.json"' in response.get_data(as_text=True)


def test_docs_page_loads_pinned_swagger_ui_assets(client: FlaskClient) -> None:
    """SPEC-PLT-13 · TC-PLT-13b"""
    html = client.get("/docs").get_data(as_text=True)

    assert "swagger-ui-dist@5.17.14/swagger-ui.css" in html
    assert "swagger-ui-dist@5.17.14/swagger-ui-bundle.js" in html


def flask_routes(app: Flask) -> set[Route]:
    """(path, METHOD) pairs exposed by the app, with paths in OpenAPI format."""
    return {
        (FLASK_PARAM.sub(r"{\1}", rule.rule), method)
        for rule in app.url_map.iter_rules()
        if rule.endpoint != "static"
        for method in rule.methods - IGNORED_METHODS
    }


def contract_routes(client: FlaskClient) -> set[Route]:
    """(path, METHOD) pairs documented in the OpenAPI contract."""
    paths = client.get("/openapi.json").get_json()["paths"]
    return {
        (path, method.upper())
        for path, operations in paths.items()
        for method in operations
        if method in HTTP_METHODS
    }


def test_every_flask_route_is_documented_in_the_contract(app: Flask, client: FlaskClient) -> None:
    """SPEC-PLT-14 · TC-PLT-14a"""
    assert flask_routes(app) - contract_routes(client) == set()


def test_every_contract_operation_is_exposed_by_flask(app: Flask, client: FlaskClient) -> None:
    """SPEC-PLT-14 · TC-PLT-14b"""
    assert contract_routes(client) - flask_routes(app) == set()
