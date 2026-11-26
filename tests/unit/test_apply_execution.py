from decimal import Decimal

import pytest

from orders import Order, OrderRejected, Side, apply_execution, apply_fill


def sell() -> Order:
    return Order(id="o-1", side=Side.SELL, qty=Decimal("10"), limit_price=Decimal("100"))


def test_redelivery_is_found_among_fills_without_an_id():
    order = apply_fill(sell(), Decimal("2"), Decimal("101"))
    apply_execution(order, "e-1", Decimal("3"), Decimal("101"))
    before = (order.status, list(order.fills))

    assert apply_execution(order, "e-1", Decimal("3"), Decimal("101")) is order
    assert (order.status, order.fills) == before
    assert [f.execution_id for f in order.fills] == [None, "e-1"]


def test_conflicting_redelivery_on_a_filled_order_is_rejected():
    order = apply_execution(sell(), "e-1", Decimal("10"), Decimal("101"))
    before = (order.status, list(order.fills))

    with pytest.raises(OrderRejected):
        apply_execution(order, "e-1", Decimal("10"), Decimal("102"))
    assert (order.status, order.fills) == before


@pytest.mark.parametrize("qty", ["0", "-1"])
def test_new_execution_needs_a_positive_quantity(qty):
    order = sell()

    with pytest.raises(OrderRejected):
        apply_execution(order, "e-1", Decimal(qty), Decimal("101"))
    assert order.fills == []


def test_conflict_exposes_fields():
    from orders import ExecutionConflict

    order = Order(id="o-9", side=Side.BUY, qty=Decimal("10"), limit_price=Decimal("100"))
    apply_execution(order, "e-1", Decimal("4"), Decimal("99"))
    with pytest.raises(ExecutionConflict) as info:
        apply_execution(order, "e-1", Decimal("5"), Decimal("98"))
    exc = info.value
    assert (exc.order_id, exc.execution_id) == ("o-9", "e-1")
    assert exc.applied == (Decimal("4"), Decimal("99"))
    assert exc.received == (Decimal("5"), Decimal("98"))
