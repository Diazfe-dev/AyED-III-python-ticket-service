"""Application configuration loaded from the environment."""

import secrets
from collections.abc import Mapping
from typing import Any

DB_FILENAME = "tickets.db"
TESTING_SECRET_KEY = "testing-secret-key"
IN_MEMORY_DATABASE_URL = "sqlite://"
TESTING_DEFAULTS: Mapping[str, Any] = {
    "SECRET_KEY": TESTING_SECRET_KEY,
    "DATABASE_URL": IN_MEMORY_DATABASE_URL,
}
SESSION_COOKIE_POLICY: Mapping[str, Any] = {
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
}


class ConfigError(Exception):
    """Raised when the application cannot start with the given configuration."""


def load_config(
    environ: Mapping[str, str],
    overrides: Mapping[str, Any] | None,
    instance_path: str,
) -> dict[str, Any]:
    """Build the Flask configuration; overrides take precedence over the environment."""
    config: dict[str, Any] = {
        "SECRET_KEY": environ.get("SECRET_KEY"),
        "DATABASE_URL": environ.get("DATABASE_URL", f"sqlite:///{instance_path}/{DB_FILENAME}"),
    }
    overrides = overrides or {}
    if overrides.get("TESTING"):
        config.update(TESTING_DEFAULTS)
    config.update(overrides)
    config.update(SESSION_COOKIE_POLICY)
    if not config["SECRET_KEY"]:
        config["SECRET_KEY"] = _fallback_secret_key(environ, config)
    return config


def _fallback_secret_key(environ: Mapping[str, str], config: Mapping[str, Any]) -> str:
    if _is_debug(environ, config):
        return secrets.token_hex(32)
    raise ConfigError("SECRET_KEY environment variable is required outside testing and debug.")


def _is_debug(environ: Mapping[str, str], config: Mapping[str, Any]) -> bool:
    return bool(config.get("DEBUG")) or environ.get("FLASK_DEBUG") == "1"
