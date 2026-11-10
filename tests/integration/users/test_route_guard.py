import re

import pytest
from flask import Flask
from flask.testing import FlaskClient

PUBLIC_ENDPOINTS = {
    "auth.login",
    "health.health",
    "api_docs.openapi_contract",
    "api_docs.swagger_ui",
    "static",
}
IGNORED_METHODS = {"HEAD", "OPTIONS"}
ROUTE_PARAM = re.compile(r"<[^<>]+>")


def protected_routes(app: Flask) -> list[tuple[str, str]]:
    """(METHOD, path) of every non-public route, with each path parameter set to 1."""
    return [
        (method, ROUTE_PARAM.sub("1", rule.rule))
        for rule in app.url_map.iter_rules()
        if rule.endpoint not in PUBLIC_ENDPOINTS
        for method in sorted(rule.methods - IGNORED_METHODS)
    ]


@pytest.mark.usefixtures("schema")
def test_every_non_public_route_requires_a_session(app: Flask, client: FlaskClient) -> None:
    """SPEC-USR-16 · TC-USR-16d"""
    routes = protected_routes(app)

    answers = {
        (method, path): client.open(path, method=method).status_code for method, path in routes
    }

    assert routes
    assert {route: status for route, status in answers.items() if status != 401} == {}
