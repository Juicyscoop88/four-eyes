# Reject dust fills

Some venues send tiny partial fills that cost us more in fees than they are worth. Traders want to set a minimum fill size on an order (optional, none by default). A fill smaller than that is rejected, unless it is exactly what remains of the order.

## Interface

In `src/orders/model.py`, new optional field on `Order` (last field, so existing calls keep working):

```python
min_fill_qty: Decimal | None = None
```

In `src/orders/engine.py`:

```python
def is_dust(order: Order, qty: Decimal) -> bool:
    """True when qty is below the order's minimum fill and is not the whole remaining quantity."""
```

`apply_fill(order, qty, price)` keeps its signature. It raises `OrderRejected("fill below minimum fill size")` when `is_dust(order, qty)` is true. `is_dust` is exported from `orders`.

## Assumptions

- No minimum (`None`) means no check: behavior is exactly as today.
- A fill equal to the minimum is accepted; only strictly smaller is dust.
- "Exactly what remains" means `qty == order.remaining_qty`; that fill is always accepted, even below the minimum.
- Existing checks come first (terminal order, non-positive qty, qty above remaining, limit price). A rejected dust fill leaves the order unchanged.
- A `min_fill_qty` of zero or negative is treated like no minimum (nothing is smaller than it). It is not validated at construction.
- The minimum is fixed at order creation; there is no setter.
