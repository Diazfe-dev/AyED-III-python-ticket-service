import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import DuplicateUserError
from app.domain.users import Admin, Client, Representative
from app.repositories.user_repository import SqlAlchemyUserRepository


def make_client(email: str = "ana@x.com") -> Client:
    return Client(name="Ana", email=email, password_hash="hash")


def test_get_returns_the_subclass_of_the_stored_role(app: Flask, db_session: Session) -> None:
    """SPEC-USR-01 · TC-USR-01c"""
    client = make_client()
    SqlAlchemyUserRepository(db_session).add(client)
    db_session.commit()

    with app.extensions[EXTENSION_KEY]["session_factory"]() as other_session:
        found = SqlAlchemyUserRepository(other_session).get(client.id)

        assert isinstance(found, Client)
        assert found.role == "Client"


def test_find_by_email_matches_the_normalized_email(db_session: Session) -> None:
    """SPEC-USR-03 · TC-USR-03c"""
    repository = SqlAlchemyUserRepository(db_session)
    client = make_client("ana@x.com")
    repository.add(client)
    db_session.commit()

    assert repository.find_by_email(" ANA@x.com ") is client


def test_adding_a_second_user_with_the_same_email_raises_duplicate_user_error(
    db_session: Session,
) -> None:
    """SPEC-USR-04 · TC-USR-04c"""
    repository = SqlAlchemyUserRepository(db_session)
    repository.add(make_client("ana@x.com"))

    with pytest.raises(DuplicateUserError):
        repository.add(make_client("ANA@x.com"))


def test_changing_an_email_to_a_taken_one_raises_duplicate_user_error(
    db_session: Session,
) -> None:
    """SPEC-USR-08 · TC-USR-08c"""
    repository = SqlAlchemyUserRepository(db_session)
    first, second = make_client("ana@x.com"), make_client("bea@x.com")
    repository.add(first)
    repository.add(second)
    db_session.commit()

    second.email = "ana@x.com"
    with pytest.raises(DuplicateUserError):
        repository.add(second)


@pytest.fixture
def one_user_per_role(db_session: Session) -> SqlAlchemyUserRepository:
    repository = SqlAlchemyUserRepository(db_session)
    for role_class, email in [
        (Representative, "rep@x.com"),
        (Admin, "admin@x.com"),
        (Client, "client@x.com"),
    ]:
        repository.add(role_class(name="User", email=email, password_hash="hash"))
    db_session.commit()
    return repository


def test_list_by_role_returns_only_clients(one_user_per_role: SqlAlchemyUserRepository) -> None:
    """SPEC-USR-11 · TC-USR-11a"""
    users = one_user_per_role.list_by_role("Client")

    assert [(type(user), user.email) for user in users] == [(Client, "client@x.com")]


def test_list_by_role_returns_only_representatives(
    one_user_per_role: SqlAlchemyUserRepository, db_session: Session
) -> None:
    """SPEC-USR-12 · TC-USR-12a"""
    one_user_per_role.add(Representative(name="Other", email="rep2@x.com", password_hash="h"))
    db_session.commit()

    users = one_user_per_role.list_by_role("Representative")

    assert [user.email for user in users] == ["rep@x.com", "rep2@x.com"]
    assert all(isinstance(user, Representative) for user in users)


def test_repository_has_no_way_to_delete_users() -> None:
    """SPEC-USR-10 · TC-USR-10b"""
    public_names = {name for name in dir(SqlAlchemyUserRepository) if not name.startswith("_")}

    assert not {name for name in public_names if "delete" in name or "remove" in name}
