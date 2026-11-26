from decimal import Decimal

from orders.model import TERMINAL, CancelReason, Fill, Order, OrderStatus, Side


class OrderRejected(Exception):
    pass


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

    order.fills.append(Fill(qty=qty, price=price))
    order.status = OrderStatus.FILLED if order.remaining_qty == 0 else OrderStatus.PARTIALLY_FILLED
    return order


def cancel(order: Order) -> Order:
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    order.status = OrderStatus.CANCELED
    return order


def cancel_with_reason(order: Order, reason: CancelReason) -> Order:
    """Cancel an order and record why.

    Raises OrderRejected if the order is already filled or canceled, or if reason is
    not a CancelReason. Sets status and cancel_reason together; the reason never changes.
    """
    raise NotImplementedError
