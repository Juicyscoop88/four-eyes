from decimal import Decimal as D

import pytest

from orders import Order, OrderRejected, OrderStatus, Side, apply_fill, cancel


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
