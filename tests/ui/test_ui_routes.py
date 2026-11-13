from pathlib import Path

import pytest
from flask.testing import FlaskClient

from app.domain.users import User
from tests.conftest import LoginAs

STATIC_ROOT = Path(__file__).resolve().parents[2] / "app" / "static"


@pytest.mark.usefixtures("schema")
def test_root_serves_the_interface_page_without_a_session(client: FlaskClient) -> None:
    """SPEC-UI-01 serves the interface page at the root without a session (TC-UI-01a)"""
    response = client.get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b'<script type="module" src="/static/js/app.js">' in response.data


@pytest.mark.usefixtures("schema")
def test_root_serves_the_same_page_with_and_without_a_session(
    client: FlaskClient, login_as: LoginAs, admin: User
) -> None:
    """SPEC-UI-01 returns the same bytes with and without a session (TC-UI-01b)"""
    anonymous = client.get("/")
    login_as(client, admin)
    authenticated = client.get("/")

    assert anonymous.status_code == authenticated.status_code == 200
    assert anonymous.data == authenticated.data == (STATIC_ROOT / "index.html").read_bytes()


@pytest.mark.usefixtures("schema")
def test_static_stylesheet_is_served_without_a_session(client: FlaskClient) -> None:
    """SPEC-UI-02 serves a static file with its content type without a session (TC-UI-02a)"""
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert response.mimetype == "text/css"


@pytest.mark.usefixtures("schema")
def test_missing_static_file_answers_a_json_not_found(client: FlaskClient) -> None:
    """SPEC-UI-03 answers 404 JSON for a missing static file (TC-UI-03a)"""
    response = client.get("/static/no-existe.js")

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


@pytest.mark.usefixtures("schema")
def test_static_directory_answers_a_json_not_found_without_listing(client: FlaskClient) -> None:
    """SPEC-UI-03 answers 404 JSON for a directory without listing files (TC-UI-03b)"""
    response = client.get("/static/css/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}
    assert b"app.css" not in response.data


@pytest.mark.usefixtures("schema")
@pytest.mark.parametrize("path", ["/static/../app/__init__.py", "/static/%2e%2e/app/__init__.py"])
def test_static_path_traversal_answers_a_json_not_found(client: FlaskClient, path: str) -> None:
    """SPEC-UI-03 answers 404 JSON for path traversal without leaking code (TC-UI-03c)"""
    response = client.get(path)

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}
    assert b"create_app" not in response.data


@pytest.mark.usefixtures("schema")
def test_application_script_is_served_as_javascript(client: FlaskClient) -> None:
    """SPEC-UI-02 serves the application script as JavaScript without a session (TC-UI-02b)"""
    response = client.get("/static/js/app.js")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


@pytest.mark.usefixtures("schema")
@pytest.mark.parametrize(
    "path",
    [
        "/static/js/core/routes.js",
        "/static/js/core/session.js",
        "/static/js/dom/render.js",
        "/static/js/dom/shell.js",
        "/static/js/screens/index.js",
        "/static/js/screens/boot.js",
    ],
)
def test_imported_modules_are_served_as_javascript(client: FlaskClient, path: str) -> None:
    """SPEC-UI-02 serves every imported module as JavaScript without a session (TC-UI-02c)"""
    response = client.get(path)

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"
