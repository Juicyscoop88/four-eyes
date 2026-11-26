"""Blind tests for: Fills counted twice after a redelivery.

Written from the task and invariants/orders.yaml only, without the implementation.
"""

from decimal import Decimal

import pytest

from orders import (
    Fill,
    Order,
    OrderRejected,
    OrderStatus,
    Side,
    apply_execution,
    cancel,
)


def buy(qty: str = "10", limit: str = "100") -> Order:
    return Order(id="o-1", side=Side.BUY, qty=Decimal(qty), limit_price=Decimal(limit))


def sell(qty: str = "10", limit: str = "100") -> Order:
    return Order(id="o-1", side=Side.SELL, qty=Decimal(qty), limit_price=Decimal(limit))


def snapshot(order: Order):
    return (order.status, list(order.fills))


# New executions


def test_new_execution_is_applied_and_fill_carries_id():
    """A new execution id is validated like apply_fill, and the appended Fill carries the id."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("99"))
    assert order.fills == [Fill(Decimal("4"), Decimal("99"), "e-1")]
    assert order.filled_qty == Decimal("4")
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_different_ids_of_same_order_are_all_applied():
    """Different executions of the same order are still all applied."""
    order = buy()
    order = apply_execution(order, "e-1", Decimal("3"), Decimal("99"))
    order = apply_execution(order, "e-2", Decimal("7"), Decimal("98"))
    assert [f.execution_id for f in order.fills] == ["e-1", "e-2"]
    assert order.filled_qty == Decimal("10")
    assert order.status is OrderStatus.FILLED


def test_two_ids_with_equal_content_are_two_executions():
    """Assumption 7: two different ids with equal qty and price are two executions."""
    order = buy()
    order = apply_execution(order, "e-1", Decimal("2"), Decimal("99"))
    order = apply_execution(order, "e-2", Decimal("2"), Decimal("99"))
    assert len(order.fills) == 2
    assert order.filled_qty == Decimal("4")


def test_new_execution_for_exact_remaining_fills_order():
    """ORD-1 and ORD-4: a new execution of exactly the remaining qty fills the order."""
    order = apply_execution(buy(), "e-1", Decimal("6"), Decimal("100"))
    order = apply_execution(order, "e-2", Decimal("4"), Decimal("100"))
    assert order.remaining_qty == Decimal("0")
    assert order.status is OrderStatus.FILLED


def test_new_execution_one_over_remaining_is_rejected():
    """Assumption 7 and ORD-1: a new execution beyond the remaining qty is rejected, order unchanged."""
    order = apply_execution(buy(), "e-1", Decimal("6"), Decimal("100"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-2", Decimal("5"), Decimal("100"))
    assert snapshot(order) == before


@pytest.mark.parametrize(
    "make, price",
    [(buy, Decimal("100.01")), (sell, Decimal("99.99"))],
    ids=["buy-above-limit", "sell-below-limit"],
)
def test_new_execution_through_limit_is_rejected(make, price):
    """Assumption 7 and ORD-2: a buy is never filled above its limit, a sell never below it."""
    order = make()
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-1", Decimal("1"), price)
    assert order.fills == []
    assert order.status is OrderStatus.NEW


def test_new_execution_on_filled_order_is_rejected():
    """Assumption 7 and ORD-3: any new execution on a filled order is rejected."""
    order = apply_execution(buy(), "e-1", Decimal("10"), Decimal("100"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-2", Decimal("1"), Decimal("100"))
    assert snapshot(order) == before


def test_new_execution_on_canceled_order_is_rejected():
    """Assumption 7 and ORD-3: any new execution on a canceled order is rejected."""
    order = cancel(buy())
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-1", Decimal("1"), Decimal("100"))
    assert snapshot(order) == before


# Redelivery


def test_redelivery_returns_order_unchanged():
    """Applying the same execution twice must not change the order a second time (assumption 1)."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("99"))
    before = snapshot(order)
    order = apply_execution(order, "e-1", Decimal("4"), Decimal("99"))
    assert snapshot(order) == before
    assert order.filled_qty == Decimal("4")


def test_redelivery_after_later_executions_is_still_ignored():
    """Applying the same execution twice must not change the order, also after other executions."""
    order = buy()
    order = apply_execution(order, "e-1", Decimal("3"), Decimal("99"))
    order = apply_execution(order, "e-2", Decimal("3"), Decimal("99"))
    before = snapshot(order)
    order = apply_execution(order, "e-1", Decimal("3"), Decimal("99"))
    assert snapshot(order) == before


def test_redelivery_compares_values_as_numbers():
    """Assumption 3: Decimal("100") equals Decimal("100.0"), so this is a redelivery."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("100"))
    before = snapshot(order)
    order = apply_execution(order, "e-1", Decimal("4.00"), Decimal("100.0"))
    assert snapshot(order) == before


def test_redelivery_of_completing_fill_on_filled_order():
    """Assumption 2: redelivery of the fill that completed an order returns it unchanged."""
    order = apply_execution(buy(), "e-1", Decimal("10"), Decimal("100"))
    before = snapshot(order)
    order = apply_execution(order, "e-1", Decimal("10"), Decimal("100"))
    assert snapshot(order) == before
    assert order.status is OrderStatus.FILLED


def test_redelivery_on_canceled_order():
    """Assumption 2: redelivery of an applied execution to a canceled order returns it unchanged."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("100"))
    order = cancel(order)
    before = snapshot(order)
    order = apply_execution(order, "e-1", Decimal("4"), Decimal("100"))
    assert snapshot(order) == before
    assert order.status is OrderStatus.CANCELED


@pytest.mark.parametrize(
    "qty, price",
    [(Decimal("5"), Decimal("99")), (Decimal("4"), Decimal("98.99")), (Decimal("3"), Decimal("99"))],
    ids=["qty-one-more", "price-differs", "qty-one-less"],
)
def test_same_id_different_content_is_rejected(qty, price):
    """Assumption 3: same id with a different qty or price raises OrderRejected, order unchanged."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("99"))
    before = snapshot(order)
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-1", qty, price)
    assert snapshot(order) == before


# Ids


def test_empty_id_is_rejected():
    """Assumption 5: an empty id is rejected with OrderRejected, order unchanged."""
    order = buy()
    with pytest.raises(OrderRejected):
        apply_execution(order, "", Decimal("1"), Decimal("100"))
    assert order.fills == []
    assert order.status is OrderStatus.NEW


def test_same_id_on_two_orders_is_applied_to_both():
    """Assumption 4: the same id on two different orders is applied to both."""
    a = Order(id="o-a", side=Side.BUY, qty=Decimal("10"), limit_price=Decimal("100"))
    b = Order(id="o-b", side=Side.BUY, qty=Decimal("10"), limit_price=Decimal("100"))
    a = apply_execution(a, "e-1", Decimal("4"), Decimal("100"))
    b = apply_execution(b, "e-1", Decimal("4"), Decimal("100"))
    assert a.filled_qty == Decimal("4")
    assert b.filled_qty == Decimal("4")


@pytest.mark.parametrize("other_id", ["E-1", "e-1 ", " e-1"], ids=["case", "trailing-space", "leading-space"])
def test_ids_are_compared_exactly(other_id):
    """Assumption 4: ids are compared exactly, case and whitespace count."""
    order = apply_execution(buy(), "e-1", Decimal("4"), Decimal("99"))
    order = apply_execution(order, other_id, Decimal("4"), Decimal("99"))
    assert len(order.fills) == 2
    assert order.filled_qty == Decimal("8")


def test_rejected_execution_leaves_no_trace():
    """Assumption 6: a rejected report is not remembered, so its id is checked again as new."""
    order = apply_execution(buy(), "e-1", Decimal("6"), Decimal("100"))
    with pytest.raises(OrderRejected):
        apply_execution(order, "e-2", Decimal("5"), Decimal("100"))
    order = apply_execution(order, "e-2", Decimal("4"), Decimal("100"))
    assert order.fills[-1] == Fill(Decimal("4"), Decimal("100"), "e-2")
    assert order.status is OrderStatus.FILLED
