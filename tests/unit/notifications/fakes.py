"""Notification strategy doubles: nothing is ever sent for real."""

from app.domain.errors import NotificationError
from app.domain.users import User


class RecordingStrategy:
    """Records every `send` instead of delivering it."""

    def __init__(self) -> None:
        self.sent: list[tuple[User, str]] = []

    def send(self, recipient: User, message: str) -> None:
        self.sent.append((recipient, message))


class FailingStrategy:
    """Fails every `send` with a `NotificationError`."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def send(self, recipient: User, message: str) -> None:
        raise NotificationError(self.reason)
