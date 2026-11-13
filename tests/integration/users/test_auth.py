import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.auth import USER_ID_KEY, admin_required, login_required
from tests.conftest import LoginAs, MakeUser


@pytest.fixture
def guarded_routes(app: Flask, schema: None) -> None:
    """Test-only routes on the fixture app, never in create_app (see the PLT-14 sync test)."""

    @app.get("/test/protected")
    @login_required
    def protected() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/test/admin-only")
    @admin_required
    def admin_only() -> dict[str, bool]:
        return {"ok": True}


@pytest.mark.usefixtures("guarded_routes")
def test_protected_route_without_session_requires_authentication(client: FlaskClient) -> None:
    """SPEC-USR-49 · TC-USR-49c"""
    response = client.get("/test/protected")

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_required"}


@pytest.mark.usefixtures("guarded_routes")
def test_session_of_a_deactivated_user_counts_as_no_session(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, db_session: Session
) -> None:
    """SPEC-USR-49 · TC-USR-49d"""
    user = make_user()
    login_as(client, user)
    user.deactivate()
    db_session.commit()

    assert client.get("/test/protected").status_code == 401


@pytest.mark.usefixtures("guarded_routes")
def test_session_of_an_unknown_user_counts_as_no_session(client: FlaskClient) -> None:
    """SPEC-USR-49 · TC-USR-49e"""
    with client.session_transaction() as session:
        session[USER_ID_KEY] = 9999

    assert client.get("/test/protected").status_code == 401


@pytest.mark.usefixtures("guarded_routes")
def test_admin_route_with_client_session_is_forbidden(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs
) -> None:
    """SPEC-USR-18 · TC-USR-18a"""
    login_as(client, make_user(role="Client"))

    response = client.get("/test/admin-only")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.usefixtures("guarded_routes")
def test_admin_route_with_admin_session_is_allowed(admin_client: FlaskClient) -> None:
    """SPEC-USR-18 · TC-USR-18d"""
    response = admin_client.get("/test/admin-only")

    assert response.status_code == 200
