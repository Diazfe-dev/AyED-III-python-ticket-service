from flask.testing import FlaskClient


def test_health_reports_ok(client: FlaskClient) -> None:
    """SPEC-PLT-11 · TC-PLT-11a"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_does_not_require_authentication(client: FlaskClient) -> None:
    """SPEC-PLT-11 · TC-PLT-11b"""
    response = client.get("/health", follow_redirects=False)

    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers
