from decimal import Decimal as D

import pytest

from orders import Order, OrderRejected, Side, apply_fill, is_dust


def make(min_fill):
    return Order("o", Side.BUY, D(10), D(100), min_fill_qty=min_fill)


def test_dust_rejected_and_unchanged():
    o = make(D(5))
    with pytest.raises(OrderRejected, match="minimum fill"):
        apply_fill(o, D(4), D(100))
    assert o.fills == []


def test_boundary_and_remaining():
    o = make(D(5))
    assert not is_dust(o, D(5))
    apply_fill(o, D(8), D(100))
    assert not is_dust(o, D(2))
    assert is_dust(o, D(1))


def test_no_minimum():
    assert not is_dust(make(None), D("0.01"))
    assert not is_dust(make(D(0)), D("0.01"))
