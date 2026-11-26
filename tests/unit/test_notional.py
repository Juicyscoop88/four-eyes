from decimal import Decimal as D

from orders import Order, Side, apply_fill, cancel, filled_notional, notional


def test_example():
    o = Order("1", Side.BUY, D(10), D(100))
    assert filled_notional(o) == 0
    apply_fill(o, D(4), D(99))
    assert notional(o) == 1000
    assert filled_notional(o) == 396


def test_canceled_keeps_values_and_read_only():
    o = Order("1", Side.SELL, D(5), D("2.5"))
    apply_fill(o, D(2), D("2.6"))
    cancel(o)
    assert notional(o) == D("12.5")
    assert filled_notional(o) == D("5.2")
    assert len(o.fills) == 1
