from types import SimpleNamespace

import pytest

from tests.conftest import MakeCategory, MakeProduct, MakeProductType, MakeTicket, MakeUser


@pytest.fixture
def world(
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> SimpleNamespace:
    """`ana` and `beto` (clients), `raul` and `rosa` (representatives) and the ticket of
    `ana` and `raul` with the product `xps`."""
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    raul = make_user("Representative", name="Raul")
    rosa = make_user("Representative", name="Rosa")
    xps = make_product(make_product_type(make_category("Hardware"), "Notebook"), "XPS 13")
    ticket = make_ticket(ana, raul, [xps])
    return SimpleNamespace(ana=ana, beto=beto, raul=raul, rosa=rosa, xps=xps, ticket=ticket)
