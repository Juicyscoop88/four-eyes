"""Blind tests for "Show what an order is worth": notional() and filled_notional().

Written from the task, its assumptions A1-A6 and invariants/orders.yaml, without the implementation.
"""

from copy import deepcopy
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from orders import (
    Fill,
    Order,
    OrderRejected,
    OrderStatus,
    Side,
    apply_fill,
    cancel,
    filled_notional,
    notional,
)

D = Decimal


def make(side=Side.BUY, qty="10", limit="100", fills=(), status=None):
    """An order built directly, with a status consistent with its fills (ORD-4)."""
    fills = [Fill(D(q), D(p)) for q, p in fills]
    filled = sum((f.qty for f in fills), D(0))
    if status is None:
        if not fills:
            status = OrderStatus.NEW
        elif filled < D(qty):
            status = OrderStatus.PARTIALLY_FILLED
        else:
            status = OrderStatus.FILLED
    return Order(id="o-1", side=side, qty=D(qty), limit_price=D(limit), status=status, fills=fills)


def snapshot(order: Order):
    return (order.id, order.side, order.qty, order.limit_price, order.status, list(order.fills))


# --- The example and the two formulas -------------------------------------------------------


def test_task_example_buy_10_at_100_with_4_filled_at_99():
    """Example: a buy of 10 at a limit of 100, 4 filled at 99, is worth 1000 at the limit, 396 filled."""
    order = make(fills=[("4", "99")])
    assert notional(order) == D("1000")
    assert filled_notional(order) == D("396")


def test_notional_uses_limit_price_not_fill_prices():
    """A1: notional is qty * limit_price, whatever the fills were priced at."""
    order = make(qty="10", limit="100", fills=[("3", "95"), ("2", "90")])
    assert notional(order) == D("1000")


def test_filled_notional_sums_each_fill_at_its_own_price():
    """A2: filled notional is the sum of fill.qty * fill.price over the fills, not filled_qty * limit."""
    order = make(qty="10", limit="100", fills=[("3", "99"), ("2", "98.5"), ("5", "100")])
    # 297 + 197 + 500; at the limit it would be 1000
    assert filled_notional(order) == D("994")


def test_no_fills_means_filled_notional_zero():
    """A4: an order with no fills has a filled notional of 0."""
    order = make(qty="7", limit="12.5")
    assert filled_notional(order) == D("0")
    assert isinstance(filled_notional(order), Decimal)
    assert notional(order) == D("87.5")


def test_results_are_decimal_not_float():
    """Interface: both functions return a Decimal (money is never a float)."""
    order = make(fills=[("4", "99")])
    assert type(notional(order)) is Decimal
    assert type(filled_notional(order)) is Decimal


def test_exact_product_without_rounding():
    """A3: no rounding, the result is the exact Decimal product."""
    order = make(qty="0.003", limit="123.456789", fills=[("0.001", "123.4567"), ("0.0015", "0.3333")])
    assert notional(order) == D("0.370370367")
    # 0.1234567 + 0.00049995
    assert filled_notional(order) == D("0.12395665")


def test_sell_order_uses_same_formulas_without_sign():
    """A1/A2: a sell is worth qty * limit_price and its fills qty * price, same as a buy."""
    order = make(side=Side.SELL, qty="10", limit="100", fills=[("4", "101")])
    assert notional(order) == D("1000")
    assert filled_notional(order) == D("404")


# --- Boundaries ------------------------------------------------------------------------------


def test_fully_filled_at_limit_filled_equals_notional():
    """A1+A2 boundary: all qty filled exactly at the limit price makes filled notional equal notional."""
    order = make(qty="10", limit="100", fills=[("6", "100"), ("4", "100")])
    assert order.status is OrderStatus.FILLED
    assert filled_notional(order) == notional(order) == D("1000")


def test_fully_filled_buy_below_limit_is_worth_less_filled():
    """A2 with ORD-2: a buy fully filled below its limit has filled notional under its notional."""
    order = make(qty="10", limit="100", fills=[("10", "99.99")])
    assert filled_notional(order) == D("999.90")
    assert filled_notional(order) < notional(order)


def test_fully_filled_sell_above_limit_is_worth_more_filled():
    """A2 with ORD-2: a sell fully filled above its limit has filled notional over its notional."""
    order = make(side=Side.SELL, qty="10", limit="100", fills=[("10", "100.01")])
    assert filled_notional(order) == D("1000.10")
    assert filled_notional(order) > notional(order)


# --- Canceled orders (A5) --------------------------------------------------------------------


def test_canceled_partially_filled_keeps_full_notional_and_its_fills():
    """A5: a canceled order keeps its notional (full order qty) and its filled notional."""
    order = make(fills=[("4", "99")], status=OrderStatus.CANCELED)
    assert notional(order) == D("1000")
    assert filled_notional(order) == D("396")


def test_canceled_through_engine_keeps_values():
    """A5 with ORD-3: cancel() after a partial fill changes neither notional nor filled notional."""
    order = make(qty="10", limit="100")
    apply_fill(order, D("4"), D("99"))
    before = (notional(order), filled_notional(order))
    cancel(order)
    assert order.status is OrderStatus.CANCELED
    assert (notional(order), filled_notional(order)) == before == (D("1000"), D("396"))


def test_canceled_without_fills_keeps_notional_and_zero_filled():
    """A4 + A5: a canceled order with no fills keeps its full notional and has 0 filled."""
    order = make(qty="10", limit="100")
    cancel(order)
    assert notional(order) == D("1000")
    assert filled_notional(order) == D("0")


# --- Read-only and interaction with fills ----------------------------------------------------


@pytest.mark.parametrize(
    "order",
    [
        make(),
        make(fills=[("4", "99")]),
        make(fills=[("10", "99")]),
        make(fills=[("4", "99")], status=OrderStatus.CANCELED),
    ],
    ids=["new", "partial", "filled", "canceled"],
)
def test_functions_never_change_the_order(order):
    """Interface: both are read-only, they never change the order (and so cannot move a terminal one, ORD-3)."""
    before = deepcopy(snapshot(order))
    first = (notional(order), filled_notional(order))
    second = (notional(order), filled_notional(order))
    assert snapshot(order) == before
    assert first == second


def test_filled_notional_follows_fills_applied_by_engine():
    """A2/A6: filled notional is derived from the fills, so it tracks each apply_fill on the order."""
    order = make(qty="10", limit="100")
    apply_fill(order, D("4"), D("99"))
    assert filled_notional(order) == D("396")
    apply_fill(order, D("6"), D("98"))
    assert order.status is OrderStatus.FILLED
    assert filled_notional(order) == D("984")
    assert notional(order) == D("1000")


def test_rejected_overfill_does_not_change_filled_notional():
    """ORD-1 + A2: a fill rejected for exceeding the remaining qty adds nothing to the filled notional."""
    order = make(qty="10", limit="100")
    apply_fill(order, D("4"), D("99"))
    with pytest.raises(OrderRejected):
        apply_fill(order, D("7"), D("99"))
    assert filled_notional(order) == D("396")
    assert notional(order) == D("1000")


qty = st.integers(min_value=1, max_value=1_000).map(Decimal)
price = st.integers(min_value=1, max_value=200).map(lambda p: Decimal(p) / 2)
step = st.one_of(
    st.tuples(st.just("fill"), qty, price),
    st.tuples(st.just("cancel"), st.none(), st.none()),
)
orders = st.builds(Order, id=st.just("o-1"), side=st.sampled_from(Side), qty=qty, limit_price=price)


@settings(max_examples=300)
@given(orders, st.lists(step, max_size=12))
def test_worth_matches_formulas_and_limit_bound_after_any_steps(order, steps):
    """A1/A2 with ORD-1 and ORD-2: after any fills and cancels, the worth matches its formulas and the limit bounds it."""
    for kind, q, p in steps:
        try:
            if kind == "fill":
                apply_fill(order, q, p)
            else:
                cancel(order)
        except OrderRejected:
            pass
        assert notional(order) == order.qty * order.limit_price
        assert filled_notional(order) == sum((f.qty * f.price for f in order.fills), D(0))
        at_limit = order.filled_qty * order.limit_price
        if order.side is Side.BUY:
            assert filled_notional(order) <= at_limit <= notional(order)
        else:
            assert filled_notional(order) >= at_limit
