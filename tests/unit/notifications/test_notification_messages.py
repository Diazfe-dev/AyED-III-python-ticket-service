from types import SimpleNamespace

import pytest

from app.services import notification_messages as messages

EVENTS = [
    (messages.ticket_created, "New", ["created"], []),
    (messages.milestone_added, "New", ["milestone"], ["InProgress"]),
    (messages.milestone_and_state_changed, "InProgress", ["milestone", "InProgress"], []),
    (messages.ticket_closed, "Closed", ["closed", "Closed"], []),
    (messages.ticket_reopened, "InProgress", ["reopened", "InProgress"], []),
]


@pytest.mark.parametrize(("build", "state_name", "expected", "absent"), EVENTS)
def test_message_identifies_the_ticket_and_the_event(build, state_name, expected, absent):
    """SPEC-NTF-18 · TC-NTF-18a"""
    ticket = SimpleNamespace(id=7, state_name=state_name)

    text = build(ticket)

    assert "#7" in text
    for word in expected:
        assert word in text
    for word in absent:
        assert word not in text


def test_the_five_messages_are_different():
    """SPEC-NTF-18 · TC-NTF-18a"""
    ticket = SimpleNamespace(id=7, state_name="InProgress")

    texts = {build(ticket) for build, *_ in EVENTS}

    assert len(texts) == 5
