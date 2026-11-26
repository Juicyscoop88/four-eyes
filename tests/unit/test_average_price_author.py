from decimal import Decimal as D
from decimal import Inexact, Rounded, localcontext

from orders import Fill, Order, Side


def order(*fills):
    return Order(
        id="o-1",
        side=Side.BUY,
        qty=D("100"),
        limit_price=D("100"),
        fills=[Fill(D(q), D(p)) for q, p in fills],
    )


def test_none_without_fills():
    assert order().average_fill_price is None


def test_weighted_with_six_places():
    assert str(order(("1", "10"), ("3", "20")).average_fill_price) == "17.500000"


def test_ties_go_to_even():
    assert str(order(("1", "1.0000005")).average_fill_price) == "1.000000"
    assert str(order(("1", "1.0000015")).average_fill_price) == "1.000002"


def test_strict_caller_context_does_not_matter():
    # A caller that traps any inexact or rounded Decimal operation still gets the number.
    o = order(("1", "1"), ("2", "2"))
    with localcontext() as ctx:
        ctx.prec = 1
        ctx.traps[Inexact] = True
        ctx.traps[Rounded] = True
        assert str(o.average_fill_price) == "1.666667"
