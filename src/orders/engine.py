from decimal import Decimal

from orders.model import TERMINAL, Fill, Order, OrderStatus, Side


class OrderRejected(Exception):
    pass


def is_dust(order: Order, qty: Decimal) -> bool:
    """True when qty is below the order's minimum fill and is not the whole remaining quantity."""
    if order.min_fill_qty is None:
        return False
    return qty < order.min_fill_qty and qty != order.remaining_qty


def apply_fill(order: Order, qty: Decimal, price: Decimal) -> Order:
    """Apply one execution report to an order."""
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    if qty <= 0:
        raise OrderRejected("fill quantity must be positive")
    if qty > order.remaining_qty:
        raise OrderRejected("fill exceeds remaining quantity")
    if order.side is Side.BUY and price > order.limit_price:
        raise OrderRejected("buy fill above limit price")
    if order.side is Side.SELL and price < order.limit_price:
        raise OrderRejected("sell fill below limit price")

    if is_dust(order, qty):
        raise OrderRejected("fill below minimum fill size")

    order.fills.append(Fill(qty=qty, price=price))
    order.status = OrderStatus.FILLED if order.remaining_qty == 0 else OrderStatus.PARTIALLY_FILLED
    return order


def cancel(order: Order) -> Order:
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    order.status = OrderStatus.CANCELED
    return order
