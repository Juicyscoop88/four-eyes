from decimal import Decimal

import pytest

from orders import CancelReason, Order, OrderRejected, OrderStatus, Side, cancel_with_reason


def make():
    return Order("o", Side.BUY, Decimal(1), Decimal(1))


def test_records_reason():
    o = cancel_with_reason(make(), CancelReason.VENUE)
    assert (o.status, o.cancel_reason) == (OrderStatus.CANCELED, CancelReason.VENUE)


def test_invalid_reason_leaves_order():
    o = make()
    with pytest.raises(OrderRejected):
        cancel_with_reason(o, "venue")
    assert (o.status, o.cancel_reason) == (OrderStatus.NEW, None)


def test_reason_not_overwritten():
    o = cancel_with_reason(make(), CancelReason.TRADER)
    with pytest.raises(OrderRejected):
        cancel_with_reason(o, CancelReason.VENUE)
    assert o.cancel_reason is CancelReason.TRADER
