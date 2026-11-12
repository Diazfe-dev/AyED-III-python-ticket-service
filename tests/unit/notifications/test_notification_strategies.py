import ast
from pathlib import Path

from app.domain.errors import DomainError, NotificationError
from app.domain.notifications import (
    MailNotification,
    WhatsappNotification,
    default_strategies,
)
from app.domain.users import NOTIFICATION_CHANNELS, Client

ALLOWED_IMPORTS = {"sqlalchemy", "app", "collections", "datetime", "typing"}
NOTIFICATIONS_MODULE = Path(__file__).resolve().parents[3] / "app" / "domain" / "notifications.py"


def test_default_strategies_cover_every_channel_and_mail_is_a_mail_strategy():
    """SPEC-NTF-01 · TC-NTF-01b"""
    strategies = default_strategies()

    assert set(strategies) == NOTIFICATION_CHANNELS
    assert isinstance(strategies["mail"], MailNotification)


def test_default_strategies_use_the_whatsapp_strategy_for_whatsapp():
    """SPEC-NTF-02 · TC-NTF-02b"""
    assert isinstance(default_strategies()["whatsapp"], WhatsappNotification)


def test_notification_error_is_a_domain_error_with_the_reason_as_text():
    """SPEC-NTF-04 · TC-NTF-04b"""
    error = NotificationError("SMTP down")

    assert isinstance(error, DomainError)
    assert str(error) == "SMTP down"


def test_simulated_strategies_send_without_raising():
    """SPEC-NTF-12 · TC-NTF-12a"""
    ana = Client(name="Ana")

    assert MailNotification().send(ana, "m") is None
    assert WhatsappNotification().send(ana, "m") is None


def test_domain_notifications_module_imports_nothing_that_reaches_the_network():
    """SPEC-NTF-12 · TC-NTF-12b"""
    tree = ast.parse(NOTIFICATIONS_MODULE.read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert imported <= ALLOWED_IMPORTS
