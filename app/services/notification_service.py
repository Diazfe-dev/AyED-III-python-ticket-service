"""Delivers notifications through the recipient's preferred channel and records them."""

from collections.abc import Callable, Mapping
from datetime import datetime

from app.domain.errors import NotificationError
from app.domain.notifications import NotificationStrategy
from app.domain.ticket import Ticket
from app.domain.users import User


class NotificationService:
    def __init__(
        self,
        strategies: Mapping[str, NotificationStrategy],
        clock: Callable[[], datetime],
        commit: Callable[[], None],
    ) -> None:
        self._strategies = strategies
        self._clock = clock
        self._commit = commit

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None:
        """Send the message to the recipient and record it on the ticket."""
        if recipient is actor:
            return
        channel = recipient.preferred_channel
        strategy = self._strategies[channel]
        now = self._clock()
        try:
            strategy.send(recipient, message)
        except NotificationError as error:
            ticket.record_failed_notification(recipient, channel, message, now, str(error))
        else:
            ticket.record_notification(recipient, channel, message, now)
        self._commit()
