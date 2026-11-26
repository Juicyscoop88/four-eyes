"""Blind tests for: Amend the quantity of a working order.

Written from the task and invariants/orders.yaml only, never from the implementation.
"""

from decimal import Decimal

import pytest

from orders import (
    Fill,
    Order,
    OrderRejected,
    OrderStatus,
    Side,
    amend_quantity,
    apply_fill,
    cancel,
)

LIMIT = Decimal("100")


def new_order(qty: str = "10", side: Side = Side.BUY) -> Order:
    return Order(id="o-1", side=side, qty=Decimal(qty), limit_price=LIMIT)


def partially_filled(qty: str = "10", filled: str = "4") -> Order:
    order = new_order(qty)
    apply_fill(order, Decimal(filled), LIMIT)
    assert order.status is OrderStatus.PARTIALLY_FILLED
    return order


def snapshot(order: Order):
    return (order.id, order.side, order.qty, order.limit_price, order.status, list(order.fills))


# Normal cases


def test_increase_partially_filled_counts_total_not_remaining():
    """Assumption 1: with 4 of 10 filled, new_qty=12 leaves 8 to fill."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("12"))
    assert order.qty == Decimal("12")
    assert order.filled_qty == Decimal("4")
    assert order.remaining_qty == Decimal("8")
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_amend_returns_same_object_and_keeps_identity_and_fills():
    """Assumptions 9 and 10: changed in place, returned; id, side, limit price and fills stay."""
    order = partially_filled("10", "4")
    fills_before = list(order.fills)
    result = amend_quantity(order, Decimal("7"))
    assert result is order
    assert order.id == "o-1"
    assert order.side is Side.BUY
    assert order.limit_price == LIMIT
    assert order.fills == fills_before == [Fill(Decimal("4"), LIMIT)]
    assert order.qty == Decimal("7")


@pytest.mark.parametrize("new_qty", ["1", "5", "25"])
def test_new_order_amended_up_or_down_stays_new(new_qty):
    """Assumption 6: NEW stays NEW, whether size goes up or down."""
    order = new_order("10", side=Side.SELL)
    amend_quantity(order, Decimal(new_qty))
    assert order.qty == Decimal(new_qty)
    assert order.status is OrderStatus.NEW
    assert order.fills == []


def test_same_quantity_on_working_order_changes_nothing():
    """Assumption 7: same quantity on a working order is accepted and changes nothing."""
    for order in (new_order("10"), partially_filled("10", "4")):
        before = snapshot(order)
        assert amend_quantity(order, Decimal("10")) is order
        assert snapshot(order) == before


# Boundaries around the filled quantity


def test_equal_to_filled_quantity_becomes_filled():
    """Assumption 5 (ORD-4): new_qty equal to the filled quantity makes the order FILLED."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("4"))
    assert order.qty == Decimal("4")
    assert order.remaining_qty == Decimal("0")
    assert order.status is OrderStatus.FILLED
    assert order.fills == [Fill(Decimal("4"), LIMIT)]


def test_one_above_filled_quantity_stays_partially_filled():
    """Assumption 6 (ORD-4): one above the filled quantity keeps PARTIALLY_FILLED."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("5"))
    assert order.qty == Decimal("5")
    assert order.remaining_qty == Decimal("1")
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_one_below_filled_quantity_is_rejected_and_unchanged():
    """Assumptions 4 and 9 (ORD-1): below the filled quantity is rejected, not rounded up."""
    order = partially_filled("10", "4")
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal("3"))
    assert snapshot(order) == before


def test_closing_by_amend_is_final():
    """Assumption 5 (ORD-3): the FILLED order from an amend never changes again."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("4"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_fill(order, Decimal("1"), LIMIT)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal("10"))
    try:
        cancel(order)
    except OrderRejected:
        pass
    assert snapshot(order) == before


# Rejections of the input


@pytest.mark.parametrize("new_qty", ["0", "-0", "-1", "-0.0001"])
@pytest.mark.parametrize("make", [new_order, partially_filled], ids=["new", "partial"])
def test_zero_or_negative_is_rejected_and_unchanged(make, new_qty):
    """Assumptions 3 and 9: zero or negative new_qty is rejected and changes nothing."""
    order = make()
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal(new_qty))
    assert snapshot(order) == before


@pytest.mark.parametrize("new_qty", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("make", [new_order, partially_filled], ids=["new", "partial"])
def test_not_finite_is_rejected_and_unchanged(make, new_qty):
    """Assumptions 8 and 9: NaN or infinite new_qty raises OrderRejected and changes nothing."""
    order = make()
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal(new_qty))
    assert snapshot(order) == before


# Terminal orders (ORD-3)


@pytest.mark.parametrize("new_qty", ["5", "10", "11"])
def test_filled_order_cannot_be_amended(new_qty):
    """Assumption 2 (ORD-3): a FILLED order is rejected, even to the same or a larger quantity."""
    order = new_order("10")
    apply_fill(order, Decimal("10"), LIMIT)
    assert order.status is OrderStatus.FILLED
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal(new_qty))
    assert snapshot(order) == before


@pytest.mark.parametrize("new_qty", ["4", "5", "10", "11"])
@pytest.mark.parametrize("make", [new_order, partially_filled], ids=["new", "partial"])
def test_canceled_order_cannot_be_amended(make, new_qty):
    """Assumption 2 (ORD-3): a CANCELED order is rejected, even to the same or a larger quantity."""
    order = make()
    cancel(order)
    assert order.status is OrderStatus.CANCELED
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        amend_quantity(order, Decimal(new_qty))
    assert snapshot(order) == before


# Interaction with later fills


def test_after_reduction_fill_beyond_new_remaining_is_rejected():
    """Assumptions 9 and 13 (ORD-1): later fills are checked against the reduced quantity."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("6"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_fill(order, Decimal("3"), LIMIT)
    assert snapshot(order) == before
    assert order.filled_qty <= order.qty


def test_after_reduction_fill_of_exact_remaining_fills_order():
    """Assumption 9 (ORD-4): a fill of exactly the new remaining quantity makes the order FILLED."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("6"))
    apply_fill(order, Decimal("2"), LIMIT)
    assert order.filled_qty == Decimal("6")
    assert order.status is OrderStatus.FILLED


def test_after_increase_fill_beyond_old_quantity_is_accepted():
    """Assumptions 1 and 9: after an increase, fills up to the new total are accepted."""
    order = partially_filled("10", "4")
    amend_quantity(order, Decimal("12"))
    apply_fill(order, Decimal("7"), LIMIT)
    assert order.filled_qty == Decimal("11")
    assert order.status is OrderStatus.PARTIALLY_FILLED
    apply_fill(order, Decimal("1"), LIMIT)
    assert order.status is OrderStatus.FILLED
    assert order.filled_qty == order.qty == Decimal("12")


def test_new_order_amended_then_filled_partially():
    """Assumption 9 (ORD-4): status after an amend still follows the fills against the new quantity."""
    order = new_order("10")
    amend_quantity(order, Decimal("3"))
    apply_fill(order, Decimal("2"), LIMIT)
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.remaining_qty == Decimal("1")
