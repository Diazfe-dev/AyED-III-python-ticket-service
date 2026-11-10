"""Test doubles shared by the unit tests of every area."""


class CommitSpy:
    """Stands in for `session.commit` and counts the calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
