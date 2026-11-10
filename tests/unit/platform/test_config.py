import pytest

from app.config import ConfigError, load_config

INSTANCE_PATH = "/srv/instance"


def test_secret_key_is_read_from_environment() -> None:
    """SPEC-PLT-01 · TC-PLT-01a"""
    config = load_config({"SECRET_KEY": "s3cret"}, None, INSTANCE_PATH)

    assert config["SECRET_KEY"] == "s3cret"


def test_database_url_is_read_from_environment() -> None:
    """SPEC-PLT-01 · TC-PLT-01b"""
    environ = {"SECRET_KEY": "s3cret", "DATABASE_URL": "sqlite:///x.db"}

    config = load_config(environ, None, INSTANCE_PATH)

    assert config["DATABASE_URL"] == "sqlite:///x.db"


def test_overrides_take_precedence_over_environment() -> None:
    """SPEC-PLT-01 · TC-PLT-01b"""
    environ = {"SECRET_KEY": "s3cret", "DATABASE_URL": "sqlite:///x.db"}

    config = load_config(environ, {"DATABASE_URL": "sqlite:///y.db"}, INSTANCE_PATH)

    assert config["DATABASE_URL"] == "sqlite:///y.db"


def test_missing_database_url_defaults_to_file_in_instance_folder() -> None:
    """SPEC-PLT-02 · TC-PLT-02a"""
    config = load_config({"SECRET_KEY": "s3cret"}, None, INSTANCE_PATH)

    assert config["DATABASE_URL"] == f"sqlite:///{INSTANCE_PATH}/tickets.db"


def test_missing_secret_key_outside_debug_raises_config_error() -> None:
    """SPEC-PLT-03 · TC-PLT-03a"""
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        load_config({}, None, INSTANCE_PATH)


def test_missing_secret_key_in_debug_generates_random_key() -> None:
    """SPEC-PLT-03 · TC-PLT-03b"""
    config = load_config({"FLASK_DEBUG": "1"}, None, INSTANCE_PATH)

    assert config["SECRET_KEY"]


def test_missing_secret_key_with_debug_override_generates_random_key() -> None:
    """SPEC-PLT-03 · TC-PLT-03b"""
    config = load_config({}, {"DEBUG": True}, INSTANCE_PATH)

    assert config["SECRET_KEY"]
