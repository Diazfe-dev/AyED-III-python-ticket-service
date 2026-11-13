from dataclasses import dataclass

import pytest

from app.domain.errors import (
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    PermissionDeniedError,
    SelfDeactivationError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.paging import Page
from app.domain.users import Representative, User
from app.services.user_service import UserService
from tests.unit.fakes import CommitSpy
from tests.unit.users.fakes import FakePasswordHasher, FakeUserRepository


@dataclass
class ServiceUnderTest:
    service: UserService
    repository: FakeUserRepository
    commit: CommitSpy
    hasher: FakePasswordHasher


@pytest.fixture
def sut() -> ServiceUnderTest:
    repository, commit, hasher = FakeUserRepository(), CommitSpy(), FakePasswordHasher()
    return ServiceUnderTest(UserService(repository, hasher, commit), repository, commit, hasher)


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
    """SPEC-USR-26 · TC-USR-26a"""
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


def test_deactivate_user_with_unknown_id_raises_user_not_found(
    sut: ServiceUnderTest, admin: User
) -> None:
    """SPEC-USR-26 · TC-USR-26b"""
    commits_before = sut.commit.calls

    with pytest.raises(UserNotFoundError):
        sut.service.deactivate_user(999, actor=admin)

    assert sut.commit.calls == commits_before


@pytest.fixture
def one_user_per_role(sut: ServiceUnderTest) -> dict[str, User]:
    return {
        role: sut.service.create_user(role, f"{role.lower()}@x.com", role, "password1")
        for role in ("Admin", "Representative", "Client")
    }


def test_list_users_returns_only_representatives(
    sut: ServiceUnderTest, one_user_per_role: dict[str, User]
) -> None:
    """SPEC-USR-12 · TC-USR-12b"""
    assert sut.service.list_users(role="Representative") == [one_user_per_role["Representative"]]


def test_list_users_without_filters_returns_every_user_of_every_role(
    sut: ServiceUnderTest, one_user_per_role: dict[str, User]
) -> None:
    """SPEC-USR-31 · TC-USR-31a"""
    inactive = sut.service.create_user("Off", "off@x.com", "Client", "password1")
    inactive.deactivate()

    users = sut.service.list_users()

    assert {user.email for user in users} == {
        "admin@x.com",
        "representative@x.com",
        "client@x.com",
        "off@x.com",
    }


@pytest.fixture
def reference_users(sut: ServiceUnderTest) -> dict[str, User]:
    users = {}
    for name, email, role in [
        ("ana", "ana@x.com", "Client"),
        ("Beto", "beto@x.com", "Client"),
        ("Ana", "otra@x.com", "Client"),
        ("Raúl", "raul@mail.com", "Client"),
        ("Rosa", "rosa@x.com", "Representative"),
        ("Admin", "admin@x.com", "Admin"),
    ]:
        users[name] = sut.service.create_user(name, email, role, "password1")
    users["Beto"].deactivate()
    return users


def names(users: object) -> list[str]:
    assert isinstance(users, list)
    return [user.name for user in users]


@pytest.mark.usefixtures("reference_users")
def test_list_users_searches_the_name_and_the_email(sut: ServiceUnderTest) -> None:
    """SPEC-USR-43 · TC-USR-43a"""
    assert names(sut.service.list_users(q="ANA")) == ["ana", "Ana"]
    assert names(sut.service.list_users(q="mail.com")) == ["Raúl"]


@pytest.mark.usefixtures("reference_users")
def test_list_users_filters_by_active_state_written_as_text(sut: ServiceUnderTest) -> None:
    """SPEC-USR-44 · TC-USR-44a"""
    assert names(sut.service.list_users(role="Client", is_active="false")) == ["Beto"]
    assert names(sut.service.list_users(role="Client", is_active="true")) == [
        "ana",
        "Ana",
        "Raúl",
    ]


def test_list_users_rejects_an_invalid_active_state_together_with_the_page(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-USR-45 · TC-USR-45b"""
    with pytest.raises(ValidationError) as alone:
        sut.service.list_users(is_active="yes")
    with pytest.raises(ValidationError) as together:
        sut.service.list_users(is_active="yes", page="0")

    assert alone.value.fields == {"is_active": "invalid"}
    assert together.value.fields == {"is_active": "invalid", "page": "invalid"}


@pytest.mark.usefixtures("reference_users")
def test_list_users_with_a_page_returns_a_page_of_the_matches(sut: ServiceUnderTest) -> None:
    """SPEC-USR-47 · TC-USR-47a"""
    result = sut.service.list_users(role="Client", page="1")

    assert isinstance(result, Page)
    assert (result.page, result.page_size, result.total) == (1, 20, 4)


def test_list_users_orders_by_name_ignoring_case_then_id(sut: ServiceUnderTest) -> None:
    """SPEC-USR-48 · TC-USR-48b"""
    for index, name in enumerate(["beto", "Ana", "ana", "Carla"]):
        sut.service.create_user(name, f"user{index}@x.com", "Client", "password1")

    assert names(sut.service.list_users()) == ["Ana", "ana", "beto", "Carla"]


def test_list_clients_for_a_representative_shows_only_active_clients(
    sut: ServiceUnderTest, reference_users: dict[str, User]
) -> None:
    """SPEC-USR-32 · TC-USR-32a"""
    clients = sut.service.list_clients(reference_users["Rosa"])

    assert names(clients) == ["ana", "Ana", "Raúl"]


def test_list_clients_for_an_admin_shows_every_client(
    sut: ServiceUnderTest, reference_users: dict[str, User]
) -> None:
    """SPEC-USR-34 · TC-USR-34a"""
    clients = sut.service.list_clients(reference_users["Admin"])

    assert names(clients) == ["ana", "Ana", "Beto", "Raúl"]
    assert {client.role for client in clients} == {"Client"}


def test_list_clients_for_a_client_is_denied_before_looking_at_the_parameters(
    sut: ServiceUnderTest, reference_users: dict[str, User]
) -> None:
    """SPEC-USR-35 · TC-USR-35a"""
    ana = reference_users["ana"]

    for parameters in [{}, {"q": "a"}, {"is_active": "yes"}, {"page": "x"}]:
        with pytest.raises(PermissionDeniedError):
            sut.service.list_clients(ana, **parameters)


def test_list_clients_for_a_representative_searches_the_name_only(
    sut: ServiceUnderTest, reference_users: dict[str, User]
) -> None:
    """SPEC-USR-46 · TC-USR-46a"""
    rosa = reference_users["Rosa"]

    assert names(sut.service.list_clients(rosa, q="ana")) == ["ana", "Ana"]
    assert sut.service.list_clients(rosa, q="mail.com") == []


def test_list_clients_rejects_the_active_filter_of_a_representative(
    sut: ServiceUnderTest, reference_users: dict[str, User]
) -> None:
    """SPEC-USR-50 · TC-USR-50a"""
    rosa = reference_users["Rosa"]

    for value in ("true", "false"):
        with pytest.raises(PermissionDeniedError):
            sut.service.list_clients(rosa, is_active=value)
    with pytest.raises(ValidationError) as raised:
        sut.service.list_clients(rosa, is_active="yes")
    assert raised.value.fields == {"is_active": "invalid"}


def test_activate_user_reactivates_an_inactive_user(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-28 · TC-USR-28b"""
    ana.deactivate()
    commits_before = sut.commit.calls

    activated = sut.service.activate_user(ana.id)

    assert activated is ana
    assert ana.is_active is True
    assert sut.commit.calls == commits_before + 1


def test_activate_user_on_an_active_user_changes_nothing(sut: ServiceUnderTest, ana: User) -> None:
    """SPEC-USR-29 · TC-USR-29a"""
    activated = sut.service.activate_user(ana.id)

    assert activated.is_active is True


def test_activate_user_with_unknown_id_raises_user_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-USR-30 · TC-USR-30a"""
    with pytest.raises(UserNotFoundError):
        sut.service.activate_user(9999)

    assert sut.commit.calls == 0


def test_change_own_password_stores_the_hash_of_the_new_one(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-37 · TC-USR-37a"""
    commits_before = sut.commit.calls

    sut.service.change_own_password(ana, "password1", "newpassword")

    assert ana.password_hash == "hashed:newpassword"
    assert sut.commit.calls == commits_before + 1


def test_change_own_password_with_a_wrong_current_one_is_rejected(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-38 · TC-USR-38a"""
    commits_before = sut.commit.calls

    with pytest.raises(InvalidCurrentPasswordError):
        sut.service.change_own_password(ana, "wrong-pass", "newpassword")

    assert ana.password_hash == "hashed:password1"
    assert sut.commit.calls == commits_before


def test_change_own_password_rejects_a_new_one_of_seven_characters(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-39 · TC-USR-39a"""
    commits_before = sut.commit.calls

    with pytest.raises(ValidationError) as raised:
        sut.service.change_own_password(ana, "password1", "short12")

    assert raised.value.fields == {"new_password": "too_short"}
    assert sut.commit.calls == commits_before


def test_change_own_password_accepts_a_new_one_of_exactly_eight_characters(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-39 · TC-USR-39c"""
    sut.service.change_own_password(ana, "password1", "12345678")

    assert ana.password_hash == "hashed:12345678"


@pytest.mark.parametrize(
    ("current", "new", "expected"),
    [
        (None, "newpassword", {"current_password": "required"}),
        ("password1", None, {"new_password": "required"}),
        (123, "newpassword", {"current_password": "invalid"}),
        ("password1", ["x"], {"new_password": "invalid"}),
        (None, 5, {"current_password": "required", "new_password": "invalid"}),
    ],
    ids=["no-current", "no-new", "numeric-current", "list-new", "both"],
)
def test_change_own_password_reports_every_invalid_field(
    sut: ServiceUnderTest, ana: User, current: object, new: object, expected: dict[str, str]
) -> None:
    """SPEC-USR-40 · TC-USR-40a"""
    commits_before = sut.commit.calls

    with pytest.raises(ValidationError) as raised:
        sut.service.change_own_password(ana, current, new)

    assert raised.value.fields == expected
    assert sut.commit.calls == commits_before


def test_change_own_password_checks_the_format_before_the_current_password(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-40 · TC-USR-40d"""
    with pytest.raises(ValidationError):
        sut.service.change_own_password(ana, "wrong-pass", "short12")

    assert sut.hasher.verify_calls == []


def test_reset_password_stores_the_new_hash_without_asking_for_the_old_one(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-41 · TC-USR-41a"""
    commits_before = sut.commit.calls

    sut.service.reset_password(ana.id, "newpassword")

    assert ana.password_hash == "hashed:newpassword"
    assert sut.commit.calls == commits_before + 1
    assert sut.hasher.verify_calls == []


def test_reset_password_rejects_a_new_one_of_seven_characters(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-39 · TC-USR-39b"""
    commits_before = sut.commit.calls

    with pytest.raises(ValidationError) as raised:
        sut.service.reset_password(ana.id, "short12")

    assert raised.value.fields == {"new_password": "too_short"}
    assert sut.commit.calls == commits_before


def test_reset_password_accepts_a_new_one_of_exactly_eight_characters(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-39 · TC-USR-39c"""
    sut.service.reset_password(ana.id, "12345678")

    assert ana.password_hash == "hashed:12345678"


@pytest.mark.parametrize(
    ("new", "reason"), [(None, "required"), (12345678, "invalid")], ids=["missing", "numeric"]
)
def test_reset_password_reports_a_missing_or_non_text_password(
    sut: ServiceUnderTest, ana: User, new: object, reason: str
) -> None:
    """SPEC-USR-40 · TC-USR-40b"""
    commits_before = sut.commit.calls

    with pytest.raises(ValidationError) as raised:
        sut.service.reset_password(ana.id, new)

    assert raised.value.fields == {"new_password": reason}
    assert sut.commit.calls == commits_before


def test_reset_password_of_an_unknown_user_raises_user_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-USR-42 · TC-USR-42a"""
    with pytest.raises(UserNotFoundError):
        sut.service.reset_password(9999, "newpassword")

    assert sut.commit.calls == 0


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


def test_authenticate_unknown_email_still_verifies_against_the_dummy_hash(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-24 · TC-USR-24a"""
    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate("nobody@x.com", "password1")

    assert sut.hasher.verify_calls == [(sut.hasher.dummy_hash(), "password1")]


def test_authenticate_inactive_user_verifies_against_the_dummy_hash(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-24 · TC-USR-24b"""
    ana.deactivate()

    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate("ana@x.com", "password1")

    assert sut.hasher.verify_calls == [(sut.hasher.dummy_hash(), "password1")]


def test_create_user_with_non_text_values_reports_them_as_invalid(sut: ServiceUnderTest) -> None:
    """SPEC-USR-25 · TC-USR-25a"""
    fields = invalid_fields(
        sut, name=123, email=123, role=1, password=12345678, preferred_channel=["mail"]
    )

    assert fields == dict.fromkeys(
        ("name", "email", "role", "password", "preferred_channel"), "invalid"
    )
    assert sut.repository.users == {}
    assert sut.commit.calls == 0


def test_update_user_with_non_text_values_reports_them_as_invalid(
    sut: ServiceUnderTest, ana: User
) -> None:
    """SPEC-USR-25 · TC-USR-25b"""
    fields = invalid_update_fields(
        sut, ana, name=1, email=["ana@x.com"], preferred_channel={"mail": 1}
    )

    assert fields == dict.fromkeys(("name", "email", "preferred_channel"), "invalid")
    assert (ana.name, ana.email, ana.preferred_channel) == ("Ana", "ana@x.com", "mail")


@pytest.mark.parametrize(
    ("email", "password"),
    [(123, "password1"), ("ana@x.com", 12345678), (["ana@x.com"], ["password1"])],
    ids=["numeric-email", "numeric-password", "list-values"],
)
def test_authenticate_with_non_text_credentials_is_rejected(
    sut: ServiceUnderTest, ana: User, email: object, password: object
) -> None:
    """SPEC-USR-25 · TC-USR-25c"""
    with pytest.raises(InvalidCredentialsError):
        sut.service.authenticate(email, password)
