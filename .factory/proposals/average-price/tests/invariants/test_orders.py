"""Property tests for invariants/orders.yaml. Owned by people, like the invariants.

Each test drives an order through a random sequence of fills, cancels and reads of the
average fill price, and checks one invariant after every step, whatever the engine
accepted or rejected.
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from orders import Order, OrderRejected, OrderStatus, Side, apply_fill, cancel

qty = st.integers(min_value=1, max_value=1_000).map(Decimal)
price = st.integers(min_value=1, max_value=200).map(lambda p: Decimal(p) / 2)
step = st.one_of(
    st.tuples(st.just("fill"), qty, price),
    st.tuples(st.just("cancel"), st.none(), st.none()),
    st.tuples(st.just("average"), st.none(), st.none()),
)
orders = st.builds(
    Order,
    id=st.just("o-1"),
    side=st.sampled_from(Side),
    qty=qty,
    limit_price=price,
)


def run(order: Order, steps):
    """Yield the order after each step, with what it was before."""
    for kind, q, p in steps:
        before = (order.status, list(order.fills))
        try:
            if kind == "fill":
                apply_fill(order, q, p)
            elif kind == "average":
                order.average_fill_price
            else:
                cancel(order)
        except OrderRejected:
            pass
        yield before, order


@settings(max_examples=300)
@given(orders, st.lists(step, max_size=12))
def test_never_overfilled(order, steps):
    for _, o in run(order, steps):
        assert o.filled_qty <= o.qty, f"ORD-1: filled {o.filled_qty} of {o.qty}"


@settings(max_examples=300)
@given(orders, st.lists(step, max_size=12))
def test_limit_price_respected(order, steps):
    for _, o in run(order, steps):
        for f in o.fills:
            if o.side is Side.BUY:
                assert f.price <= o.limit_price, f"ORD-2: buy filled at {f.price} over {o.limit_price}"
            else:
                assert f.price >= o.limit_price, f"ORD-2: sell filled at {f.price} under {o.limit_price}"


@settings(max_examples=300)
@given(orders, st.lists(step, max_size=12))
def test_terminal_is_final(order, steps):
    for (status, fills), o in run(order, steps):
        if status in (OrderStatus.FILLED, OrderStatus.CANCELED):
            assert o.status == status and o.fills == fills, "ORD-3: a terminal order changed"


@settings(max_examples=300)
@given(orders, st.lists(step, max_size=12))
def test_status_matches_fills(order, steps):
    for _, o in run(order, steps):
        if o.status is OrderStatus.CANCELED:
            continue
        if not o.fills:
            expected = OrderStatus.NEW
        elif o.filled_qty < o.qty:
            expected = OrderStatus.PARTIALLY_FILLED
        else:
            expected = OrderStatus.FILLED
        assert o.status is expected, f"ORD-4: {o.status.value} with {o.filled_qty}/{o.qty} filled"
