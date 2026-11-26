"""Blind tests for Order.average_fill_price, written from the task only.

Fills are placed on the order directly, so each test pins the average itself and does not depend
on how apply_fill validates. One test drives apply_fill to check the interaction with a partial fill.
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal, localcontext
from fractions import Fraction

from hypothesis import given, settings
from hypothesis import strategies as st

from orders import Fill, Order, OrderStatus, Side, apply_fill

D = Decimal


def order_with(*fills, status=OrderStatus.PARTIALLY_FILLED, side=Side.BUY):
    """An order holding the given (qty, price) fills, with a limit that admits them."""
    return Order(
        id="o-1",
        side=side,
        qty=D("1000000"),
        limit_price=D("1000000000000000000000000"),
        status=status,
        fills=[Fill(qty=D(q), price=D(p)) for q, p in fills],
    )


def assert_reported(value, expected: str):
    """The value is a Decimal equal to expected and carries exactly 6 decimal places."""
    assert isinstance(value, Decimal), f"expected Decimal, got {type(value).__name__}"
    assert value == D(expected), f"{value} != {expected}"
    assert value.as_tuple().exponent == -6, f"{value} does not have exactly 6 decimal places"


def test_no_fills_is_none():
    """Issue: 'none if it has no fills yet'; assumption 2: None means Python None, not zero."""
    assert order_with(status=OrderStatus.NEW).average_fill_price is None


def test_single_whole_price_has_six_places():
    """Assumption 5: Decimal('100') is reported as 100.000000, a Decimal with exactly 6 places."""
    avg = order_with(("5", "100")).average_fill_price
    assert_reported(avg, "100.000000")
    assert str(avg) == "100.000000"


def test_volume_weighted_not_simple_mean():
    """Assumption 2: sum(qty * price) / sum(qty), so a large fill weighs more than a small one."""
    # Simple mean would be 105; weighted is (100 + 990) / 10 = 109.
    assert_reported(order_with(("1", "100"), ("9", "110")).average_fill_price, "109.000000")


def test_fractional_quantities_and_repeating_quotient():
    """Assumption 2 and issue: fractional fills, a non-terminating quotient reported to 6 places."""
    # (0.5 * 1.1 + 0.25 * 1.3) / 0.75 = 0.875 / 0.75 = 1.1666666...
    assert_reported(order_with(("0.5", "1.1"), ("0.25", "1.3")).average_fill_price, "1.166667")


def test_exact_tie_rounds_down_to_even():
    """Issue: round half to even; 1.0000005 is a tie and goes to the even 1.000000."""
    assert_reported(order_with(("1", "1.000000"), ("1", "1.000001")).average_fill_price, "1.000000")


def test_exact_tie_rounds_up_to_even():
    """Issue: round half to even; 1.0000015 is a tie and goes to the even 1.000002."""
    assert_reported(order_with(("1", "1.000001"), ("1", "1.000002")).average_fill_price, "1.000002")


def test_just_above_half_is_not_made_a_tie():
    """Assumption 3: an exact average just above halfway rounds up, no earlier rounding makes it a tie."""
    # 3.0000015001 / 3 = 1.00000050003333..., above the halfway point 1.0000005.
    order = order_with(("1", "1"), ("1", "1"), ("1", "1.0000015001"))
    assert_reported(order.average_fill_price, "1.000001")


def test_just_below_half_is_not_made_a_tie():
    """Assumption 3: an exact average just below halfway rounds down, no earlier rounding makes it a tie."""
    # 3.0000014999 / 3 = 1.00000049996666..., below the halfway point 1.0000005.
    order = order_with(("1", "1"), ("1", "1"), ("1", "1.0000014999"))
    assert_reported(order.average_fill_price, "1.000000")


def test_fill_price_is_not_rounded_before_averaging():
    """Assumption 3: fill prices are not rounded first; a price with 11 places counts in full."""
    # Rounding the price to 7 places first gives 1.0000005, a tie, and then 1.000000.
    assert_reported(order_with(("1", "1.00000050001")).average_fill_price, "1.000001")


def test_more_digits_than_default_precision():
    """Assumption 4: inputs and result with more digits than the caller's precision (28) are exact."""
    # Exact average is just above ...901.0000005; at 28 digits the product or quotient becomes a tie.
    price = "123456789012345678901.0000005000000000001"
    order = order_with(("1", price), ("1", price))
    assert_reported(order.average_fill_price, "123456789012345678901.000001")


def test_caller_low_precision_does_not_change_result():
    """Assumption 4: a caller precision below the result's digits gives the same number, no error."""
    order = order_with(("1", "100"), ("3", "104.5"))  # (100 + 313.5) / 4 = 103.375
    with localcontext() as ctx:
        ctx.prec = 3
        avg = order.average_fill_price
    assert_reported(avg, "103.375000")


def test_caller_rounding_mode_does_not_change_result():
    """Assumption 4: the caller's rounding mode does not change the result; it is always half even."""
    tie = order_with(("1", "1.000000"), ("1", "1.000001"))  # 1.0000005
    above = order_with(("1", "1"), ("1", "1"), ("1", "1.0000015001"))  # 1.00000050003...
    for mode in (ROUND_HALF_UP, ROUND_UP, ROUND_DOWN):
        with localcontext() as ctx:
            ctx.rounding = mode
            tie_avg, above_avg = tie.average_fill_price, above.average_fill_price
        assert_reported(tie_avg, "1.000000")
        assert_reported(above_avg, "1.000001")


def test_canceled_order_with_and_without_fills():
    """Assumption 6: status does not matter; canceled with fills has an average, without has None."""
    assert_reported(
        order_with(("2", "50"), status=OrderStatus.CANCELED).average_fill_price, "50.000000"
    )
    assert order_with(status=OrderStatus.CANCELED).average_fill_price is None


def test_filled_and_sell_orders_have_average():
    """Assumption 6: a fully filled order, buy or sell, reports the same average from its fills."""
    for side in Side:
        order = order_with(("1", "10"), ("1", "11"), status=OrderStatus.FILLED, side=side)
        assert_reported(order.average_fill_price, "10.500000")


def test_derived_from_current_fills_and_read_only():
    """Assumption 7: computed from the current fills, not stored, and reading it changes nothing."""
    order = order_with(("1", "100"))
    fills_before, status_before = list(order.fills), order.status
    assert_reported(order.average_fill_price, "100.000000")
    assert_reported(order.average_fill_price, "100.000000")
    assert order.fills == fills_before and order.status is status_before
    order.fills.append(Fill(qty=D("1"), price=D("102")))
    assert_reported(order.average_fill_price, "101.000000")
    order.fills.clear()
    assert order.average_fill_price is None


def test_partially_filled_through_apply_fill():
    """Issue and assumption 9: on an order partially filled by apply_fill, it averages the fills so far."""
    order = Order(id="o-1", side=Side.BUY, qty=D("10"), limit_price=D("100"))
    assert order.average_fill_price is None
    apply_fill(order, D("2"), D("100"))
    apply_fill(order, D("1"), D("97"))
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert_reported(order.average_fill_price, "99.000000")  # (200 + 97) / 3
    assert order.fills == [Fill(D("2"), D("100")), Fill(D("1"), D("97"))]


fill_qty = st.integers(min_value=1, max_value=10**9).map(lambda n: Decimal(f"{n}E-4"))
fill_price = st.integers(min_value=1, max_value=10**12).map(lambda n: Decimal(f"{n}E-8"))


@settings(max_examples=300)
@given(st.lists(st.tuples(fill_qty, fill_price), min_size=1, max_size=8))
def test_matches_exact_quotient_rounded_half_even(fills):
    """Assumptions 2, 3, 5: equals the exact rational VWAP rounded once, half to even, to 6 places."""
    order = order_with(*fills)
    exact = sum(Fraction(q) * Fraction(p) for q, p in fills) / sum(Fraction(q) for q, _ in fills)
    expected = Fraction(round(exact * 10**6), 10**6)  # round() on Fraction is half to even
    avg = order.average_fill_price
    assert isinstance(avg, Decimal) and avg.as_tuple().exponent == -6
    assert Fraction(avg) == expected, f"{avg} != {expected} for {fills}"
