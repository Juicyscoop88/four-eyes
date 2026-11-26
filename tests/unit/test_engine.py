from decimal import Decimal as D

import pytest

from orders import Order, OrderRejected, OrderStatus, Side, amend_quantity, apply_fill, cancel


def buy(qty="10", limit="100"):
    return Order(id="o-1", side=Side.BUY, qty=D(qty), limit_price=D(limit))


def test_partial_then_full_fill():
    o = buy()
    apply_fill(o, D("4"), D("99"))
    assert o.status is OrderStatus.PARTIALLY_FILLED
    apply_fill(o, D("6"), D("100"))
    assert o.status is OrderStatus.FILLED


def test_rejects_fill_after_cancel():
    o = cancel(buy())
    with pytest.raises(OrderRejected):
        apply_fill(o, D("1"), D("100"))


def test_amend_to_filled_compares_value_across_several_fractional_fills():
    o = buy("1")
    apply_fill(o, D("0.1"), D("100"))
    apply_fill(o, D("0.2"), D("100"))
    amend_quantity(o, D("0.300"))
    assert o.status is OrderStatus.FILLED


@pytest.mark.parametrize("bad", ["NaN", "sNaN", "Infinity", "0", "3.999"])
def test_rejected_amend_changes_nothing(bad):
    o = apply_fill(buy(), D("4"), D("100"))
    with pytest.raises(OrderRejected):
        amend_quantity(o, D(bad))
    assert (o.qty, o.status, o.filled_qty) == (D("10"), OrderStatus.PARTIALLY_FILLED, D("4"))


def test_rejects_amend_after_cancel():
    o = cancel(buy())
    with pytest.raises(OrderRejected):
        amend_quantity(o, D("12"))
    assert (o.qty, o.status) == (D("10"), OrderStatus.CANCELED)
