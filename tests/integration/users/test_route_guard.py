import re

import pytest
from flask import Flask
from flask.testing import FlaskClient

PUBLIC_ROUTES = {
    ("POST", "/login"),
    ("GET", "/"),
    ("GET", "/static/<path:filename>"),
    ("GET", "/health"),
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
}
IGNORED_METHODS = {"HEAD", "OPTIONS"}
ROUTE_PARAM = re.compile(r"<[^<>]+>")
AUTHENTICATION_REQUIRED = {"error": "authentication_required"}


def protected_routes(app: Flask) -> list[tuple[str, str]]:
    """(METHOD, path) of every route outside the closed public list, each parameter set to 1."""
    return [
        (method, ROUTE_PARAM.sub("1", rule.rule))
        for rule in app.url_map.iter_rules()
        for method in sorted(rule.methods - IGNORED_METHODS)
        if (method, rule.rule) not in PUBLIC_ROUTES
    ]


@pytest.mark.usefixtures("schema")
def test_every_non_public_route_requires_a_session(app: Flask, client: FlaskClient) -> None:
    """SPEC-USR-49 · TC-USR-49a"""
    routes = protected_routes(app)

    answers = {(method, path): client.open(path, method=method) for method, path in routes}

    assert routes
    assert {
        route: response.status_code
        for route, response in answers.items()
        if response.get_json(silent=True) != AUTHENTICATION_REQUIRED
    } == {}
    assert {response.status_code for response in answers.values()} == {401}


@pytest.mark.usefixtures("schema")
@pytest.mark.parametrize(
    ("method", "path", "status", "error"),
    [
        ("POST", "/login", 401, "invalid_credentials"),
        ("GET", "/health", 200, None),
        ("GET", "/docs", 200, None),
        ("GET", "/openapi.json", 200, None),
    ],
)
def test_public_routes_answer_without_a_session(
    client: FlaskClient, method: str, path: str, status: int, error: str | None
) -> None:
    """SPEC-USR-49 · TC-USR-49b"""
    response = client.open(path, method=method, json={} if method == "POST" else None)

    assert response.status_code == status
    assert response.get_json(silent=True) != AUTHENTICATION_REQUIRED
    if error is not None:
        assert response.get_json() == {"error": error}
