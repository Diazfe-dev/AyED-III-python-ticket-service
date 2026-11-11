"""Test doubles shared by the unit tests of every area."""

from datetime import UTC, datetime, timedelta


class CommitSpy:
    """Stands in for `session.commit` and counts the calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class FakeClock:
    """A clock fixed at a UTC instant that only moves when the test advances it."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
