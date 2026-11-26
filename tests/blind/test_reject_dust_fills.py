"""Blind tests for the task "Reject dust fills". Written without seeing the implementation."""

from decimal import Decimal

import pytest

from orders import Fill, Order, OrderRejected, OrderStatus, Side, apply_fill, cancel, is_dust

DUST = "fill below minimum fill size"


def make(qty="10", min_fill=None, side=Side.BUY, limit="100"):
    return Order(
        id="o-1",
        side=side,
        qty=Decimal(qty),
        limit_price=Decimal(limit),
        min_fill_qty=None if min_fill is None else Decimal(min_fill),
    )


def snapshot(order):
    return (order.status, list(order.fills), order.filled_qty)


# --- is_dust -------------------------------------------------------------------

def test_is_dust_none_minimum_is_never_dust():
    """No minimum (None) means no check."""
    order = make(qty="10")
    assert is_dust(order, Decimal("0.0001")) is False


def test_is_dust_strictly_below_minimum():
    """A fill smaller than the minimum is dust (one tick below the boundary)."""
    order = make(qty="10", min_fill="5")
    assert is_dust(order, Decimal("4.99")) is True


def test_is_dust_equal_to_minimum_is_not_dust():
    """A fill equal to the minimum is accepted; only strictly smaller is dust."""
    order = make(qty="10", min_fill="5")
    assert is_dust(order, Decimal("5")) is False
    assert is_dust(order, Decimal("5.00")) is False


def test_is_dust_above_minimum_is_not_dust():
    """Only strictly smaller than the minimum is dust (one tick above the boundary)."""
    order = make(qty="10", min_fill="5")
    assert is_dust(order, Decimal("5.01")) is False


def test_is_dust_whole_remaining_below_minimum_is_not_dust():
    """'Exactly what remains' (qty == order.remaining_qty) is always accepted, even below the minimum."""
    order = make(qty="10", min_fill="5")
    apply_fill(order, Decimal("7"), Decimal("100"))
    assert order.remaining_qty == Decimal("3")
    assert is_dust(order, Decimal("3")) is False
    assert is_dust(order, Decimal("2.99")) is True


@pytest.mark.parametrize("minimum", ["0", "-1"])
def test_is_dust_zero_or_negative_minimum_is_no_minimum(minimum):
    """A min_fill_qty of zero or negative is treated like no minimum."""
    order = make(qty="10", min_fill=minimum)
    assert is_dust(order, Decimal("0.0001")) is False


# --- apply_fill ----------------------------------------------------------------

def test_apply_fill_rejects_dust_and_leaves_order_unchanged():
    """apply_fill raises OrderRejected('fill below minimum fill size'); a rejected dust fill leaves the order unchanged."""
    order = make(qty="10", min_fill="5")
    before = snapshot(order)
    with pytest.raises(OrderRejected, match=DUST):
        apply_fill(order, Decimal("4.99"), Decimal("100"))
    assert snapshot(order) == before
    assert order.status is OrderStatus.NEW


def test_apply_fill_accepts_fill_equal_to_minimum():
    """A fill equal to the minimum is accepted."""
    order = make(qty="10", min_fill="5")
    apply_fill(order, Decimal("5"), Decimal("100"))
    assert order.fills == [Fill(Decimal("5"), Decimal("100"))]
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_apply_fill_without_minimum_accepts_tiny_fill():
    """No minimum (None) means behavior is exactly as today: a tiny fill is accepted."""
    order = make(qty="10")
    apply_fill(order, Decimal("0.01"), Decimal("100"))
    assert order.filled_qty == Decimal("0.01")
    assert order.status is OrderStatus.PARTIALLY_FILLED


@pytest.mark.parametrize("minimum", ["0", "-5"])
def test_apply_fill_zero_or_negative_minimum_accepts_tiny_fill(minimum):
    """A min_fill_qty of zero or negative is treated like no minimum and is not validated at construction."""
    order = make(qty="10", min_fill=minimum)
    apply_fill(order, Decimal("0.01"), Decimal("100"))
    assert order.filled_qty == Decimal("0.01")


def test_partially_filled_order_accepts_remaining_below_minimum_and_fills():
    """'Exactly what remains' is always accepted even below the minimum; status matches fills (ORD-4)."""
    order = make(qty="10", min_fill="5")
    apply_fill(order, Decimal("8"), Decimal("100"))
    apply_fill(order, Decimal("2"), Decimal("100"))
    assert order.filled_qty == Decimal("10")
    assert order.status is OrderStatus.FILLED


def test_partially_filled_order_rejects_dust_below_remaining():
    """A partially filled order still rejects a dust fill that is not the whole remainder, unchanged afterwards."""
    order = make(qty="10", min_fill="5")
    apply_fill(order, Decimal("8"), Decimal("100"))
    before = snapshot(order)
    with pytest.raises(OrderRejected, match=DUST):
        apply_fill(order, Decimal("1.99"), Decimal("100"))
    assert snapshot(order) == before
    assert order.status is OrderStatus.PARTIALLY_FILLED


def test_minimum_larger_than_order_accepts_whole_order_only():
    """A fill below the minimum is accepted only when it is exactly what remains."""
    order = make(qty="3", min_fill="5", side=Side.SELL, limit="50")
    with pytest.raises(OrderRejected, match=DUST):
        apply_fill(order, Decimal("2"), Decimal("50"))
    apply_fill(order, Decimal("3"), Decimal("50"))
    assert order.status is OrderStatus.FILLED


# --- order of checks -------------------------------------------------------------

def test_terminal_check_comes_before_dust_check():
    """Existing checks come first: a canceled order rejects any fill for being terminal, not as dust (ORD-3)."""
    order = make(qty="10", min_fill="5")
    cancel(order)
    with pytest.raises(OrderRejected) as exc:
        apply_fill(order, Decimal("1"), Decimal("100"))
    assert str(exc.value) != DUST
    assert order.status is OrderStatus.CANCELED and order.fills == []


@pytest.mark.parametrize("qty", ["0", "-1"])
def test_non_positive_check_comes_before_dust_check(qty):
    """Existing checks come first: a non-positive qty is rejected by the existing check, not as dust."""
    order = make(qty="10", min_fill="5")
    with pytest.raises(OrderRejected) as exc:
        apply_fill(order, Decimal(qty), Decimal("100"))
    assert str(exc.value) != DUST
    assert order.fills == []


def test_overfill_check_comes_before_dust_check():
    """Existing checks come first: qty above remaining is rejected as overfill, not dust (ORD-1)."""
    order = make(qty="10", min_fill="5")
    apply_fill(order, Decimal("8"), Decimal("100"))
    with pytest.raises(OrderRejected) as exc:
        apply_fill(order, Decimal("3"), Decimal("100"))
    assert str(exc.value) != DUST
    assert order.filled_qty == Decimal("8")


@pytest.mark.parametrize("side, price", [(Side.BUY, "100.5"), (Side.SELL, "99.5")])
def test_limit_price_check_comes_before_dust_check(side, price):
    """Existing checks come first: a fill through the limit is rejected for price, not as dust (ORD-2)."""
    order = make(qty="10", min_fill="5", side=side, limit="100")
    with pytest.raises(OrderRejected) as exc:
        apply_fill(order, Decimal("1"), Decimal(price))
    assert str(exc.value) != DUST
    assert order.fills == [] and order.status is OrderStatus.NEW
