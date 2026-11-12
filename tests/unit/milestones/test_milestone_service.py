import pytest

from app.domain.errors import (
    PermissionDeniedError,
    TicketClosedError,
    TicketNotFoundError,
    ValidationError,
)
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative
from app.services.ticket_service import TicketService
from tests.unit.catalog.fakes import FakeProductRepository
from tests.unit.fakes import CommitSpy, FakeClock
from tests.unit.tickets.fakes import FakeTicketNotifier, FakeTicketRepository
from tests.unit.users.fakes import FakeUserRepository


class Setup:
    def __init__(self) -> None:
        self.tickets = FakeTicketRepository()
        self.users = FakeUserRepository()
        self.clock = FakeClock()
        self.commit = CommitSpy()
        self.notifier = FakeTicketNotifier()
        self.service = TicketService(
            self.tickets,
            self.users,
            FakeProductRepository(),
            self.clock.now,
            self.commit,
            self.notifier,
        )
        self.ana = Client(name="Ana", email="ana@example.com", is_active=True)
        self.beto = Client(name="Beto", email="beto@example.com", is_active=True)
        self.raul = Representative(name="Raul", email="raul@example.com", is_active=True)
        self.rosa = Representative(name="Rosa", email="rosa@example.com", is_active=True)
        self.root = Admin(name="Root", email="root@example.com", is_active=True)
        for user in (self.ana, self.beto, self.raul, self.rosa, self.root):
            self.users.add(user)
        self.ticket = self.add_ticket()

    def add_ticket(self) -> Ticket:
        ticket = Ticket.open(self.ana, self.raul, [], "Hola", self.clock.now())
        self.tickets.add(ticket)
        return ticket


@pytest.fixture
def setup() -> Setup:
    return Setup()


@pytest.mark.parametrize("in_progress", [False, True])
def test_representative_milestone_is_saved_with_one_commit(setup, in_progress):
    """SPEC-MLS-01 · TC-MLS-01b"""
    if in_progress:
        setup.ticket.start_progress(setup.raul, setup.clock.now())

    milestone = setup.service.add_milestone(setup.ticket.id, "Revisando", setup.raul)

    assert setup.ticket.milestones[-1] is milestone
    assert milestone.content == "Revisando"
    assert setup.commit.calls == 1


def test_client_milestone_is_saved_with_the_client_as_author(setup):
    """SPEC-MLS-02 · TC-MLS-02b"""
    milestone = setup.service.add_milestone(setup.ticket.id, "Gracias", setup.ana)

    assert milestone.author is setup.ana
    assert setup.ticket.milestones[-1] is milestone
    assert setup.commit.calls == 1


def test_milestone_takes_the_clock_instant_and_the_caller_as_author(setup):
    """SPEC-MLS-03 · TC-MLS-03c"""
    milestone = setup.service.add_milestone(setup.ticket.id, "Hola", setup.ana)

    assert milestone.created_at == setup.clock.now()
    assert milestone.author is setup.ana


def assert_rejected_without_lookup(setup, fields, *args, **kwargs):
    with pytest.raises(ValidationError) as raised:
        setup.service.add_milestone(*args, **kwargs)
    assert raised.value.fields == fields
    assert setup.tickets.visible_lookups == []
    assert setup.commit.calls == 0


@pytest.mark.parametrize("content", [None, "", "   "])
def test_blank_content_is_required(setup, content):
    """SPEC-MLS-04 · TC-MLS-04a"""
    assert_rejected_without_lookup(
        setup, {"content": "required"}, setup.ticket.id, content, setup.raul
    )


def test_content_and_flag_errors_are_reported_together(setup):
    """SPEC-MLS-04 · TC-MLS-04b"""
    assert_rejected_without_lookup(
        setup,
        {"content": "required", "start_progress": "invalid"},
        setup.ticket.id,
        "   ",
        setup.raul,
        start_progress="yes",
    )


def test_invalid_content_is_rejected_before_looking_up_the_ticket(setup):
    """SPEC-MLS-04 · TC-MLS-04c (dec. 4)"""
    assert_rejected_without_lookup(setup, {"content": "required"}, setup.ticket.id, "", setup.beto)
    assert_rejected_without_lookup(setup, {"content": "required"}, 9999, "", setup.ana)


@pytest.mark.parametrize("content", [123, True, ["Hola"], {"a": 1}])
def test_non_text_content_is_invalid(setup, content):
    """SPEC-MLS-11 · TC-MLS-11a"""
    assert_rejected_without_lookup(
        setup, {"content": "invalid"}, setup.ticket.id, content, setup.raul
    )


@pytest.mark.parametrize("flag", [None, "yes", "true", 1, 0])
def test_non_boolean_start_progress_is_invalid(setup, flag):
    """SPEC-TKT-09 · TC-TKT-09d (dec. 7)"""
    assert_rejected_without_lookup(
        setup,
        {"start_progress": "invalid"},
        setup.ticket.id,
        "Hola",
        setup.raul,
        start_progress=flag,
    )


@pytest.mark.parametrize("actor_name, ticket_id", [("beto", None), ("rosa", None), ("ana", 9999)])
def test_unseen_ticket_is_not_found_when_adding_a_milestone(setup, actor_name, ticket_id):
    """SPEC-MLS-06 · TC-MLS-06b"""
    actor = getattr(setup, actor_name)
    target = setup.ticket.id if ticket_id is None else ticket_id

    with pytest.raises(TicketNotFoundError):
        setup.service.add_milestone(target, "Hola", actor)

    assert setup.commit.calls == 0
    assert len(setup.ticket.milestones) == 1


def test_admin_is_forbidden_to_add_milestones_before_the_ticket_lookup(setup):
    """SPEC-TKT-27 · TC-TKT-27f"""
    for ticket_id in (9999, setup.ticket.id):
        with pytest.raises(PermissionDeniedError):
            setup.service.add_milestone(ticket_id, "Hola", setup.root)

    assert setup.tickets.visible_lookups == []
    assert setup.commit.calls == 0


def test_admin_with_invalid_body_gets_the_validation_error_first(setup):
    """SPEC-TKT-27 · TC-TKT-27g (dec. 9, G-21)"""
    with pytest.raises(ValidationError):
        setup.service.add_milestone(setup.ticket.id, "", setup.root)
    with pytest.raises(ValidationError):
        setup.service.add_milestone(setup.ticket.id, "Hola", setup.root, start_progress="yes")


@pytest.mark.parametrize("start_progress", [False, True])
def test_closed_ticket_rejects_milestones_without_changes(setup, start_progress):
    """SPEC-MLS-05 · TC-MLS-05c (dec. 5)"""
    setup.ticket.close(setup.raul, setup.clock.now())
    commits = setup.commit.calls
    history = list(setup.ticket.state_history)
    actor = setup.raul if start_progress else setup.ana

    with pytest.raises(TicketClosedError):
        setup.service.add_milestone(setup.ticket.id, "Hola", actor, start_progress=start_progress)

    assert setup.commit.calls == commits
    assert setup.ticket.state_name == "Closed"
    assert len(setup.ticket.milestones) == 1
    assert setup.ticket.state_history == history


def test_closed_ticket_answers_not_found_and_validation_before_closed(setup):
    """SPEC-MLS-05 · TC-MLS-05d (dec. 11)"""
    setup.ticket.close(setup.raul, setup.clock.now())

    with pytest.raises(TicketNotFoundError):
        setup.service.add_milestone(setup.ticket.id, "Hola", setup.beto)
    with pytest.raises(ValidationError):
        setup.service.add_milestone(setup.ticket.id, "", setup.ana)


def test_start_progress_moves_a_new_ticket_in_progress_with_one_commit(setup):
    """SPEC-TKT-09 · TC-TKT-09e"""
    milestone = setup.service.add_milestone(
        setup.ticket.id, "Empiezo", setup.raul, start_progress=True
    )

    change = setup.ticket.state_history[-1]
    assert setup.ticket.state_name == "InProgress"
    assert (change.user, change.state_name, change.timestamp) == (
        setup.raul,
        "InProgress",
        setup.clock.now(),
    )
    assert setup.ticket.milestones[-1] is milestone
    assert setup.commit.calls == 1


def test_start_progress_on_an_in_progress_ticket_keeps_the_state(setup):
    """SPEC-MLS-01 · TC-MLS-01d (dec. 5)"""
    setup.ticket.start_progress(setup.raul, setup.clock.now())
    history = list(setup.ticket.state_history)

    setup.service.add_milestone(setup.ticket.id, "Sigo", setup.raul, start_progress=True)

    assert setup.ticket.state_name == "InProgress"
    assert setup.ticket.state_history == history
    assert len(setup.ticket.milestones) == 2
    assert setup.commit.calls == 1


@pytest.mark.parametrize("flag", [None, False])
def test_milestone_without_the_flag_keeps_a_new_ticket_new(setup, flag):
    """SPEC-MLS-01 · TC-MLS-01e"""
    history = list(setup.ticket.state_history)
    arguments = {} if flag is None else {"start_progress": flag}

    setup.service.add_milestone(setup.ticket.id, "Revisando", setup.raul, **arguments)

    assert setup.ticket.state_name == "New"
    assert setup.ticket.state_history == history
    assert len(setup.ticket.milestones) == 2


def test_client_start_progress_is_ignored(setup):
    """SPEC-MLS-02 · TC-MLS-02c (dec. 6)"""
    history = list(setup.ticket.state_history)

    setup.service.add_milestone(setup.ticket.id, "Gracias", setup.ana, start_progress=True)

    assert setup.ticket.state_name == "New"
    assert setup.ticket.state_history == history
    assert len(setup.ticket.milestones) == 2


def test_milestone_and_state_change_share_a_single_clock_read(setup):
    """SPEC-MLS-03 · TC-MLS-03e"""
    reads = []

    def counting_clock():
        reads.append(1)
        setup.clock.advance(1)
        return setup.clock.now()

    service = TicketService(
        setup.tickets,
        setup.users,
        FakeProductRepository(),
        counting_clock,
        setup.commit,
        setup.notifier,
    )

    milestone = service.add_milestone(setup.ticket.id, "Empiezo", setup.raul, start_progress=True)

    assert len(reads) == 1
    assert milestone.created_at == setup.ticket.state_history[-1].timestamp


@pytest.mark.parametrize("actor_name, ticket_id", [("beto", None), ("rosa", None), ("ana", 9999)])
def test_unseen_ticket_is_not_found_when_listing_milestones(setup, actor_name, ticket_id):
    """SPEC-MLS-06 · TC-MLS-06c"""
    actor = getattr(setup, actor_name)
    target = setup.ticket.id if ticket_id is None else ticket_id

    with pytest.raises(TicketNotFoundError):
        setup.service.list_milestones(target, actor)


def test_participants_list_the_milestones_in_ticket_order(setup):
    """SPEC-MLS-07 · TC-MLS-07a"""
    setup.service.add_milestone(setup.ticket.id, "Revisando", setup.raul)
    setup.service.add_milestone(setup.ticket.id, "Gracias", setup.ana)

    for actor in (setup.ana, setup.raul):
        listed = setup.service.list_milestones(setup.ticket.id, actor)
        assert listed == list(setup.ticket.milestones)
        assert [m.content for m in listed] == ["Hola", "Revisando", "Gracias"]


def test_closed_ticket_milestones_can_be_listed(setup):
    """SPEC-MLS-07 · TC-MLS-07d (G-05)"""
    setup.ticket.close(setup.raul, setup.clock.now())

    listed = setup.service.list_milestones(setup.ticket.id, setup.ana)

    assert listed == list(setup.ticket.milestones)


def test_admin_is_forbidden_to_list_milestones_before_the_ticket_lookup(setup):
    """SPEC-TKT-27 · TC-TKT-27f (list_milestones)"""
    for ticket_id in (9999, setup.ticket.id):
        with pytest.raises(PermissionDeniedError):
            setup.service.list_milestones(ticket_id, setup.root)

    assert setup.tickets.visible_lookups == []
    assert setup.commit.calls == 0
