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


def apply_execution(order: Order, execution_id: str, qty: Decimal, price: Decimal) -> Order:
    """Apply a venue execution report to an order, at most once per execution id.

    A new execution id is validated like apply_fill, and the appended Fill carries the id.
    Redelivery of an applied id with equal qty and price returns the order unchanged, also
    when the order is filled or canceled. Raises OrderRejected, leaving the order unchanged,
    if the id is empty, if an applied id arrives with a different qty or price, or if
    apply_fill would reject a new execution.
    """
    raise NotImplementedError


def cancel(order: Order) -> Order:
    if order.status in TERMINAL:
        raise OrderRejected(f"order {order.id} is {order.status.value}")
    order.status = OrderStatus.CANCELED
    return order
