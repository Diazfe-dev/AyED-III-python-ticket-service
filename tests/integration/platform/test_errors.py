import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.domain.errors import UserNotFoundError


def test_unknown_route_answers_json_not_found(client: FlaskClient) -> None:
    """SPEC-PLT-15 · TC-PLT-15a"""
    response = client.get("/no-such-route")

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("PATCH", "/categories/abc"),
        ("PATCH", "/users/abc"),
        ("POST", "/users/abc/deactivate"),
    ],
)
def test_non_numeric_id_in_the_url_answers_json_not_found(
    client: FlaskClient, method: str, path: str
) -> None:
    """SPEC-PLT-15 · TC-PLT-15b"""
    response = client.open(path, method=method)

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


def test_method_not_exposed_answers_json_method_not_allowed(client: FlaskClient) -> None:
    """SPEC-PLT-15 · TC-PLT-15c"""
    response = client.delete("/health")

    assert response.status_code == 405
    assert response.get_json() == {"error": "method_not_allowed"}
    assert "GET" in response.allow


def test_unhandled_error_answers_generic_json_internal_error(unpropagated_app: Flask) -> None:
    """SPEC-PLT-16 · TC-PLT-16a"""

    @unpropagated_app.get("/test/crash")
    def crash() -> str:
        raise RuntimeError("secret-detail")

    response = unpropagated_app.test_client().get("/test/crash")

    body = response.get_data(as_text=True)
    assert response.status_code == 500
    assert response.get_json() == {"error": "internal_error"}
    assert "secret-detail" not in body
    assert "Traceback" not in body


def test_domain_errors_keep_their_own_response(unpropagated_app: Flask) -> None:
    """SPEC-PLT-16 · TC-PLT-16b"""

    @unpropagated_app.get("/test/domain-error")
    def domain_error() -> str:
        raise UserNotFoundError()

    response = unpropagated_app.test_client().get("/test/domain-error")

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


def test_http_errors_are_not_turned_into_internal_errors(unpropagated_app: Flask) -> None:
    """SPEC-PLT-16 · TC-PLT-16c"""
    response = unpropagated_app.test_client().get("/no-such-route")

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}
