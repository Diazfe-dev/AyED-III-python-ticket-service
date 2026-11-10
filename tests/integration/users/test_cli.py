import pytest
from click.testing import Result
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.users import Admin, User
from tests.conftest import MakeUser

pytestmark = pytest.mark.usefixtures("schema")


def create_admin(runner: FlaskCliRunner, password: str = "password1") -> Result:
    return runner.invoke(
        args=["create-admin", "--name", "Ana", "--email", "ana@x.com"],
        input=f"{password}\n{password}\n",
    )


def users_with_email(db_session: Session, email: str) -> list[User]:
    db_session.expire_all()
    return list(db_session.scalars(select(User).where(User.email == email)))


def test_create_admin_creates_an_active_admin(runner: FlaskCliRunner, db_session: Session) -> None:
    """SPEC-USR-20 · TC-USR-20a"""
    result = create_admin(runner)

    assert result.exit_code == 0, result.output
    assert "Admin created" in result.output
    [admin] = users_with_email(db_session, "ana@x.com")
    assert isinstance(admin, Admin)
    assert admin.is_active is True


def test_create_admin_with_taken_email_fails(
    runner: FlaskCliRunner, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-20 · TC-USR-20b"""
    make_user(email="ana@x.com")

    result = create_admin(runner)

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert len(users_with_email(db_session, "ana@x.com")) == 1


def test_create_admin_with_short_password_fails(
    runner: FlaskCliRunner, db_session: Session
) -> None:
    """SPEC-USR-20 · TC-USR-20c"""
    result = create_admin(runner, password="passwor")

    assert result.exit_code != 0
    assert "password (too_short)" in result.output
    assert users_with_email(db_session, "ana@x.com") == []


def test_create_admin_rejects_the_password_on_the_command_line(
    runner: FlaskCliRunner, db_session: Session
) -> None:
    """SPEC-USR-20 · TC-USR-20e"""
    result = runner.invoke(
        args=["create-admin", "--name", "Ana", "--email", "ana@x.com", "--password", "password1"]
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert users_with_email(db_session, "ana@x.com") == []


def test_created_admin_can_log_in(runner: FlaskCliRunner, client: FlaskClient) -> None:
    """SPEC-USR-20 · TC-USR-20d"""
    create_admin(runner)

    response = client.post("/login", json={"email": "ana@x.com", "password": "password1"})

    assert response.status_code == 200
    assert response.get_json()["role"] == "Admin"
