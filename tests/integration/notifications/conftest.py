from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.notifications import Notification
from tests.conftest import MakeCategory, MakeProduct, MakeProductType, MakeTicket, MakeUser


@pytest.fixture
def world(
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> SimpleNamespace:
    """`ana` (mail) and `wanda` (whatsapp) clients, the representative `raul`, the product
    `xps` and the ticket of `ana` and `raul`, opened without notifications."""
    ana = make_user("Client", name="Ana")
    wanda = make_user("Client", name="Wanda", preferred_channel="whatsapp")
    raul = make_user("Representative", name="Raul")
    xps = make_product(make_product_type(make_category("Hardware"), "Notebook"), "XPS 13")
    ticket = make_ticket(ana, raul, [xps])
    return SimpleNamespace(ana=ana, wanda=wanda, raul=raul, xps=xps, ticket=ticket)


def notification_rows(db_session: Session) -> list[Notification]:
    """The stored notifications ordered by id, read fresh from the database."""
    db_session.expire_all()
    return list(db_session.scalars(select(Notification).order_by(Notification.id)))
