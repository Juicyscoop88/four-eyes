from decimal import Decimal

from orders.model import TERMINAL, Fill, Order, OrderStatus, Side


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


def amend_quantity(order: Order, new_qty: Decimal) -> Order:
    """Change the total quantity (filled plus remaining) of a working order, up or down.

    The order is changed in place and returned; its id, side, limit price and fills are kept.
    If new_qty equals the filled quantity, the order becomes FILLED. Otherwise the status stays.

    Raises OrderRejected, leaving the order unchanged, if the order is FILLED or CANCELED, or if
    new_qty is not finite, not positive, or below the filled quantity.
    """
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    # Checked first: comparing a NaN raises InvalidOperation, not OrderRejected.
    if not new_qty.is_finite():
        raise OrderRejected("order quantity must be finite")
    if new_qty <= 0:
        raise OrderRejected("order quantity must be positive")
    if new_qty < order.filled_qty:
        raise OrderRejected("order quantity below filled quantity")

    order.qty = new_qty
    if order.remaining_qty == 0:
        order.status = OrderStatus.FILLED
    return order


def cancel(order: Order) -> Order:
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    order.status = OrderStatus.CANCELED
    return order
