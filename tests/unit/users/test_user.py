import pytest

from app.domain.users import ROLE_CLASSES, Admin, Client, Representative, normalize_email


@pytest.mark.parametrize(
    ("role", "role_class"),
    [("Admin", Admin), ("Representative", Representative), ("Client", Client)],
)
def test_role_registry_builds_the_subclass_of_each_role(role: str, role_class: type) -> None:
    """SPEC-USR-01 · TC-USR-01b"""
    user = ROLE_CLASSES[role](name="Ana", email="ana@x.com")

    assert type(user) is role_class
    assert user.role == role


def test_deactivate_marks_user_as_inactive() -> None:
    """SPEC-USR-09 · TC-USR-09a"""
    client = Client(name="Ana", email="ana@x.com", is_active=True)

    client.deactivate()

    assert client.is_active is False


def test_activate_marks_user_as_active() -> None:
    """SPEC-USR-28 · TC-USR-28a"""
    client = Client(name="Ana", email="ana@x.com", is_active=False)

    client.activate()

    assert client.is_active is True


def test_normalize_email_strips_spaces_and_lowercases() -> None:
    """SPEC-USR-03 · TC-USR-03a"""
    assert normalize_email("  Ana@X.COM ") == "ana@x.com"


def test_user_email_is_normalized_on_assignment() -> None:
    """SPEC-USR-03 · TC-USR-03b"""
    client = Client(email=" Ana@X.com ")

    assert client.email == "ana@x.com"
