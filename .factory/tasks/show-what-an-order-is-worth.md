# Show what an order is worth

### What should change

Every order should say how much money it is worth: its notional, and how much of that is already filled.

### Why

The risk team adds these up by hand from exports to check limits, and twice this month they got it wrong.

### An example (optional)

A buy of 10 at a limit of 100, with 4 filled at 99: worth 1000 at the limit, 396 filled.

## Interface

In `src/orders/engine.py`, exported from `orders`:

```python
def notional(order: Order) -> Decimal:
    """Worth of the whole order at its limit price: qty * limit_price."""

def filled_notional(order: Order) -> Decimal:
    """Worth of what is filled so far: the sum of fill.qty * fill.price."""
```

Both are read-only: they never change the order.

## Assumptions

- A1. Notional is `qty * limit_price`, as in the example (10 * 100 = 1000). Choice: the limit price, not a market price.
- A2. Filled notional uses each fill's own price, not the limit (4 * 99 = 396). Choice: sum over the fills.
- A3. No rounding: the result is the exact `Decimal` product. Choice: nothing is lost; a person can ask for a rounding mode later.
- A4. An order with no fills has a filled notional of 0.
- A5. A canceled order keeps its notional and filled notional as they are. Choice: no special case, the full order qty counts.
- A6. Functions in `engine.py`, not new fields on `Order`, so nothing is stored that could drift from the fills.
