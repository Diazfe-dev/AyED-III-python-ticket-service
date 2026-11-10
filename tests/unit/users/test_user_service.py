from dataclasses import dataclass

import pytest

from app.domain.errors import (
    DuplicateUserError,
    InvalidCredentialsError,
    SelfDeactivationError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.users import Representative, User
from app.services.user_service import UserService
from tests.unit.users.fakes import CommitSpy, FakePasswordHasher, FakeUserRepository


@dataclass
class ServiceUnderTest:
    service: UserService
    repository: FakeUserRepository
    commit: CommitSpy


@pytest.fixture
def sut() -> ServiceUnderTest:
    repository, commit = FakeUserRepository(), CommitSpy()
    return ServiceUnderTest(
        UserService(repository, FakePasswordHasher(), commit), repository, commit
    )


def test_create_user_stores_an_active_user_of_the_requested_role(sut: ServiceUnderTest) -> None:
    """SPEC-USR-01 · TC-USR-01a"""
    user = sut.service.create_user("Ana", "ana@x.com", "Representative", "password1")

    assert isinstance(user, Representative)
    assert user.is_active is True
    assert sut.repository.get(user.id) is user
    assert sut.commit.calls == 1


def test_create_user_keeps_only_the_password_hash(sut: ServiceUnderTest) -> None:
    """SPEC-USR-02 · TC-USR-02b"""
    user = sut.service.create_user("Ana", "ana@x.com", "Client", "password1")

    assert user.password_hash == "hashed:password1"
    stored_values = [getattr(user, column.key) for column in user.__mapper__.column_attrs]
    assert "password1" not in stored_values


def test_create_user_without_channel_assigns_mail(sut: ServiceUnderTest) -> None:
    """SPEC-USR-06 · TC-USR-06a"""
    user = sut.service.create_user("Ana", "ana@x.com", "Client", "password1")

    assert user.preferred_channel == "mail"


def test_create_user_keeps_the_requested_channel(sut: ServiceUnderTest) -> None:
    """SPEC-USR-06 · TC-USR-06b"""
    user = sut.service.create_user(
        "Ana", "ana@x.com", "Client", "password1", preferred_channel="whatsapp"
    )

    assert user.preferred_channel == "whatsapp"


def invalid_fields(sut: ServiceUnderTest, **overrides: object) -> dict[str, str]:
    data: dict[str, object] = {
        "name": "Ana",
        "email": "ana@x.com",
        "role": "Client",
        "password": "password1",
    }
    data.update(overrides)
    with pytest.raises(ValidationError) as raised:
        sut.service.create_user(**data)
    return raised.value.fields


def test_create_user_without_name_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-05 · TC-USR-05a"""
    assert invalid_fields(sut, name=None) == {"name": "required"}


def test_create_user_with_malformed_email_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-05 · TC-USR-05b"""
    assert invalid_fields(sut, email="ana-at-x") == {"email": "invalid"}


def test_create_user_with_unknown_role_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-05 · TC-USR-05c"""
    assert invalid_fields(sut, role="Superuser") == {"role": "invalid"}


def test_create_user_without_password_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-05 · TC-USR-05d"""
    assert invalid_fields(sut, password=None) == {"password": "required"}


def test_create_user_reports_every_invalid_field_at_once(sut: ServiceUnderTest) -> None:
    """SPEC-USR-05 · TC-USR-05e"""
    fields = invalid_fields(sut, name="   ", email="", role=None, password=None)

    assert fields == {
        "name": "required",
        "email": "required",
        "role": "required",
        "password": "required",
    }
    assert sut.repository.users == {}
    assert sut.commit.calls == 0


def test_create_user_with_seven_character_password_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-19 · TC-USR-19a"""
    assert invalid_fields(sut, password="passwor") == {"password": "too_short"}
    assert sut.commit.calls == 0


def test_create_user_with_exactly_eight_character_password_is_accepted(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-USR-19 · TC-USR-19b"""
    user = sut.service.create_user("Ana", "ana@x.com", "Client", "password")

    assert user.password_hash == "hashed:password"


def test_create_user_with_unknown_channel_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-23 · TC-USR-23a"""
    assert invalid_fields(sut, preferred_channel="sms") == {"preferred_channel": "invalid"}
    assert sut.repository.users == {}
    assert sut.commit.calls == 0


def test_create_user_with_taken_email_in_other_case_is_rejected_before_adding(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-USR-04 · TC-USR-04a"""
    sut.service.create_user("Ana", "ana@x.com", "Client", "password1")

    with pytest.raises(DuplicateUserError):
        sut.service.create_user("Other", "ANA@x.com ", "Client", "password1")

    assert sut.repository.add_calls == 1
    assert sut.commit.calls == 1


def test_create_user_with_email_of_inactive_user_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-USR-04 · TC-USR-04b"""
    existing = sut.service.create_user("Ana", "ana@x.com", "Client", "password1")
    existing.deactivate()

    with pytest.raises(DuplicateUserError):
        sut.service.create_user("Other", "ana@x.com", "Representative", "password1")


@pytest.fixture
def ana(sut: ServiceUnderTest) -> User:
    return sut.service.create_user("Ana", "ana@x.com", "Client", "password1")


def test_update_user_saves_name_email_and_channel(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-07 · TC-USR-07a"""
    commits_before = sut.commit.calls

    updated = sut.service.update_user(
        ana.id, name="Ana María", email=" AnaM@X.com ", preferred_channel="whatsapp"
    )

    assert (updated.name, updated.email, updated.preferred_channel) == (
        "Ana María",
        "anam@x.com",
        "whatsapp",
    )
    assert sut.commit.calls == commits_before + 1


def test_update_user_accepts_its_own_email_in_other_case(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-07 · TC-USR-07b"""
    updated = sut.service.update_user(ana.id, email="ANA@X.COM")

    assert updated.email == "ana@x.com"


def test_update_user_with_unknown_id_raises_user_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-USR-07 · TC-USR-07c"""
    with pytest.raises(UserNotFoundError):
        sut.service.update_user(999, name="Nobody")

    assert sut.commit.calls == 0


def test_update_user_to_an_email_of_another_user_is_rejected(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-08 · TC-USR-08a"""
    bea = sut.service.create_user("Bea", "bea@x.com", "Client", "password1")
    commits_before = sut.commit.calls

    with pytest.raises(DuplicateUserError):
        sut.service.update_user(ana.id, email=bea.email.upper())

    assert ana.email == "ana@x.com"
    assert sut.commit.calls == commits_before


def invalid_update_fields(sut: ServiceUnderTest, user: User, **changes: object) -> dict[str, str]:
    commits_before = sut.commit.calls
    with pytest.raises(ValidationError) as raised:
        sut.service.update_user(user.id, **changes)
    assert sut.commit.calls == commits_before
    return raised.value.fields


def test_update_user_with_blank_name_is_rejected(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-22 · TC-USR-22a"""
    assert invalid_update_fields(sut, ana, name="   ") == {"name": "required"}
    assert ana.name == "Ana"


def test_update_user_with_malformed_email_is_rejected(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-22 · TC-USR-22b"""
    assert invalid_update_fields(sut, ana, email="ana-at-x") == {"email": "invalid"}
    assert ana.email == "ana@x.com"


def test_update_user_reports_every_invalid_field_at_once(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-22 · TC-USR-22c"""
    fields = invalid_update_fields(sut, ana, name="", email="")

    assert fields == {"name": "required", "email": "required"}
    assert (ana.name, ana.email) == ("Ana", "ana@x.com")


def test_update_user_with_unknown_channel_is_rejected(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-23 · TC-USR-23b"""
    fields = invalid_update_fields(sut, ana, preferred_channel="telegram")

    assert fields == {"preferred_channel": "invalid"}
    assert ana.preferred_channel == "mail"


@pytest.fixture
def admin(sut: ServiceUnderTest) -> User:
    return sut.service.create_user("Root", "root@x.com", "Admin", "password1")


def test_deactivate_user_marks_another_user_inactive_and_keeps_it(
    sut: ServiceUnderTest, admin: User, ana: User
) -> None:
    """SPEC-USR-09 · TC-USR-09b"""
    commits_before = sut.commit.calls

    deactivated = sut.service.deactivate_user(ana.id, actor=admin)

    assert deactivated is ana
    assert ana.is_active is False
    assert sut.repository.get(ana.id) is ana
    assert sut.commit.calls == commits_before + 1


def test_admin_cannot_deactivate_itself(sut: ServiceUnderTest, admin: User) -> None:
    """SPEC-USR-21 · TC-USR-21a"""
    commits_before = sut.commit.calls

    with pytest.raises(SelfDeactivationError):
        sut.service.deactivate_user(admin.id, actor=admin)

    assert admin.is_active is True
    assert sut.commit.calls == commits_before


@pytest.fixture
def one_user_per_role(sut: ServiceUnderTest) -> dict[str, User]:
    return {
        role: sut.service.create_user(role, f"{role.lower()}@x.com", role, "password1")
        for role in ("Admin", "Representative", "Client")
    }


def test_list_by_role_returns_only_clients(
    sut: ServiceUnderTest, one_user_per_role: dict[str, User]
) -> None:
    """SPEC-USR-11 · TC-USR-11b"""
    assert sut.service.list_by_role("Client") == [one_user_per_role["Client"]]


def test_list_by_role_returns_only_representatives(
    sut: ServiceUnderTest, one_user_per_role: dict[str, User]
) -> None:
    """SPEC-USR-12 · TC-USR-12b"""
    assert sut.service.list_by_role("Representative") == [one_user_per_role["Representative"]]


def test_authenticate_returns_the_active_user_with_matching_credentials(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-14 · TC-USR-14a"""
    assert sut.service.authenticate(" ANA@x.com ", "password1") is ana


def test_authenticate_with_unknown_email_is_rejected(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-15 · TC-USR-15a"""
    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate("nobody@x.com", "password1")


def test_authenticate_with_wrong_password_is_rejected(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-15 · TC-USR-15b"""
    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate("ana@x.com", "wrong-password")


def test_authenticate_inactive_user_is_rejected_even_with_right_password(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-15 · TC-USR-15c"""
    ana.deactivate()

    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate("ana@x.com", "password1")
