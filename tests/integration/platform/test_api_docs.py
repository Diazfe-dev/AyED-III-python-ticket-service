import re

from flask import Flask
from flask.testing import FlaskClient

IGNORED_METHODS = {"HEAD", "OPTIONS"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
FLASK_PARAM = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")

Route = tuple[str, str]

UI_ROUTES = {("GET", "/"), ("GET", "/static/<path:filename>")}


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


def to_openapi_path(rule: str) -> str:
    return FLASK_PARAM.sub(r"{\1}", rule)


def flask_routes(app: Flask) -> set[Route]:
    """(path, METHOD) pairs exposed by the app, with paths in OpenAPI format."""
    return {
        (to_openapi_path(rule.rule), method)
        for rule in app.url_map.iter_rules()
        for method in rule.methods - IGNORED_METHODS
    }


def ui_routes() -> set[Route]:
    """Explicit UI routes that live outside the contract, in OpenAPI path format."""
    return {(to_openapi_path(path), method) for method, path in UI_ROUTES}


def contract_routes(client: FlaskClient) -> set[Route]:
    """(path, METHOD) pairs documented in the OpenAPI contract."""
    paths = client.get("/openapi.json").get_json()["paths"]
    return {
        (path, method.upper())
        for path, operations in paths.items()
        for method in operations
        if method in HTTP_METHODS
    }


def test_every_flask_route_is_in_the_contract_or_the_ui_set(
    app: Flask, client: FlaskClient
) -> None:
    """SPEC-PLT-23 · TC-PLT-23a"""
    assert flask_routes(app) - contract_routes(client) - ui_routes() == set()


def test_every_contract_operation_is_exposed_by_flask(app: Flask, client: FlaskClient) -> None:
    """SPEC-PLT-23 · TC-PLT-23b"""
    assert contract_routes(client) - flask_routes(app) == set()


def test_ui_static_route_exists_and_is_outside_the_contract(
    app: Flask, client: FlaskClient
) -> None:
    """SPEC-PLT-23 · TC-PLT-23c"""
    rules = {(rule.rule, method) for rule in app.url_map.iter_rules() for method in rule.methods}

    assert ("/static/<path:filename>", "GET") in rules
    assert ("/static/{filename}", "GET") not in contract_routes(client)


def test_ui_root_route_exists_and_is_outside_the_contract(app: Flask, client: FlaskClient) -> None:
    """SPEC-PLT-23 · TC-PLT-23d"""
    rules = {(rule.rule, method) for rule in app.url_map.iter_rules() for method in rule.methods}

    assert ("/", "GET") in rules
    assert ("/", "GET") not in contract_routes(client)
