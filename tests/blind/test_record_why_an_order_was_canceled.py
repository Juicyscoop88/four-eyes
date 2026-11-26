"""Blind tests for "Record why an order was canceled".

Written from the task and invariants/orders.yaml only; the implementation was not seen.
"""

from decimal import Decimal

import pytest

from orders import (
    CancelReason,
    Order,
    OrderRejected,
    OrderStatus,
    Side,
    apply_fill,
    cancel,
    cancel_with_reason,
)

QTY = Decimal("10")
LIMIT = Decimal("100.5")


def new_order(side: Side = Side.BUY) -> Order:
    return Order(id="o-1", side=side, qty=QTY, limit_price=LIMIT)


def filled(order: Order, qty: Decimal) -> Order:
    apply_fill(order, qty, LIMIT)
    return order


def snapshot(order: Order):
    return (order.status, list(order.fills), order.cancel_reason)


INVALID_REASONS = [
    None,
    "trader",
    "other",
    "unknown",
    "",
    OrderStatus.CANCELED,
    0,
]


def test_exactly_three_reasons():
    """Three reasons only: trader, risk system, venue. No free text and no other/unknown."""
    assert {r.name: r.value for r in CancelReason} == {
        "TRADER": "trader",
        "RISK_SYSTEM": "risk_system",
        "VENUE": "venue",
    }


def test_existing_construction_defaults_reason_to_none():
    """Order gets cancel_reason last, with a default, so existing construction keeps working; None until canceled."""
    order = Order("o-1", Side.SELL, QTY, LIMIT)
    assert order.cancel_reason is None
    assert order.status is OrderStatus.NEW


@pytest.mark.parametrize("reason", list(CancelReason))
@pytest.mark.parametrize("side", list(Side))
def test_cancel_new_order_records_reason(reason, side):
    """Sets status to CANCELED and cancel_reason to reason, together."""
    order = new_order(side)
    result = cancel_with_reason(order, reason)
    assert result.status is OrderStatus.CANCELED
    assert result.cancel_reason is reason
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is reason
    assert order.fills == []


@pytest.mark.parametrize("fill_qty", [Decimal("1"), QTY - Decimal("1"), QTY - Decimal("0.01")])
def test_cancel_partially_filled_order_records_reason_and_keeps_fills(fill_qty):
    """A partially filled order (one less than full) can be canceled with a reason; its fills are kept."""
    order = filled(new_order(), fill_qty)
    assert order.status is OrderStatus.PARTIALLY_FILLED
    fills_before = list(order.fills)
    result = cancel_with_reason(order, CancelReason.RISK_SYSTEM)
    assert result.status is OrderStatus.CANCELED
    assert result.cancel_reason is CancelReason.RISK_SYSTEM
    assert order.fills == fills_before


@pytest.mark.parametrize("reason", list(CancelReason))
def test_cancel_filled_order_rejected_and_untouched(reason):
    """Raises OrderRejected if the order is already filled (ORD-3); no reason is recorded."""
    order = filled(new_order(), QTY)
    assert order.status is OrderStatus.FILLED
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, reason)
    assert snapshot(order) == before
    assert order.cancel_reason is None


@pytest.mark.parametrize("first", list(CancelReason))
@pytest.mark.parametrize("second", list(CancelReason))
def test_second_cancel_never_overwrites_reason(first, second):
    """The stored reason of a canceled order is never overwritten, including by a second cancel with a different reason."""
    order = new_order()
    cancel_with_reason(order, first)
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, second)
    assert snapshot(order) == before
    assert order.cancel_reason is first


def test_plain_cancel_after_reasoned_cancel_rejected_and_reason_kept():
    """ORD-3 and 'must not change afterwards': cancel() on an order canceled with a reason is rejected and keeps the reason."""
    order = new_order()
    cancel_with_reason(order, CancelReason.VENUE)
    with pytest.raises(OrderRejected):
        cancel(order)
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is CancelReason.VENUE


def test_reasoned_cancel_after_plain_cancel_rejected_reason_stays_none():
    """Raises OrderRejected if the order is already canceled, even if canceled by cancel() without a reason."""
    order = new_order()
    cancel(order)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, CancelReason.TRADER)
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is None


def test_plain_cancel_unchanged_records_no_reason():
    """Existing cancel(order) is kept unchanged: it still cancels with cancel_reason = None."""
    order = new_order()
    cancel(order)
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is None


@pytest.mark.parametrize("bad", INVALID_REASONS)
def test_invalid_reason_rejected_on_new_order_and_untouched(bad):
    """A missing or invalid reason is rejected with OrderRejected and the order is left untouched."""
    order = new_order()
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, bad)
    assert snapshot(order) == before
    assert order.status is OrderStatus.NEW
    assert order.cancel_reason is None


@pytest.mark.parametrize("bad", INVALID_REASONS)
def test_invalid_reason_rejected_on_partially_filled_order_and_untouched(bad):
    """A missing or invalid reason leaves a partially filled order's status, fills and reason unchanged."""
    order = filled(new_order(), Decimal("4"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, bad)
    assert snapshot(order) == before
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_order_still_cancelable_after_invalid_reason():
    """A rejected invalid reason leaves the order untouched, so a later valid cancel records the valid reason."""
    order = new_order()
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, "venue")
    cancel_with_reason(order, CancelReason.VENUE)
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is CancelReason.VENUE


@pytest.mark.parametrize("bad", INVALID_REASONS)
def test_invalid_reason_on_canceled_order_does_not_change_reason(bad):
    """The reason must not change afterwards: an invalid reason on a canceled order is rejected and the reason kept."""
    order = new_order()
    cancel_with_reason(order, CancelReason.TRADER)
    with pytest.raises(OrderRejected):
        cancel_with_reason(order, bad)
    assert order.status is OrderStatus.CANCELED
    assert order.cancel_reason is CancelReason.TRADER


def test_fill_after_reasoned_cancel_rejected_and_reason_kept():
    """ORD-3: a canceled order never changes again; a late fill is rejected and the reason and fills stay."""
    order = filled(new_order(), Decimal("3"))
    cancel_with_reason(order, CancelReason.RISK_SYSTEM)
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_fill(order, Decimal("1"), LIMIT)
    assert snapshot(order) == before


def test_fills_do_not_set_a_reason():
    """Reason is None until canceled; only a canceled order has a reason (ORD-4 status from fills)."""
    order = new_order()
    filled(order, Decimal("4"))
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.cancel_reason is None
    filled(order, Decimal("6"))
    assert order.status is OrderStatus.FILLED
    assert order.cancel_reason is None
