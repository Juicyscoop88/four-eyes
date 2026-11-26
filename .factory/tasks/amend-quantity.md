# Amend the quantity of a working order

Traders want to change the size of a working order without canceling it and losing their place.
Up or down. It should keep its fills.

## Interface

In `src/orders/engine.py`, exported from `orders`:

```python
def amend_quantity(order: Order, new_qty: Decimal) -> Order:
```

`new_qty` is the new total quantity, including what is already filled. The function changes the order in
place and returns it, like `apply_fill` and `cancel`. A rejection raises `OrderRejected`.

## Assumptions

1. **Total, not remaining.** With 4 of 10 filled, `new_qty=12` leaves 8 to fill.
2. **Working order** means `NEW` or `PARTIALLY_FILLED`. Amending a `FILLED` or `CANCELED` order is
   rejected, even to the same or a larger quantity (ORD-3).
3. **Zero or negative** `new_qty` is rejected. Amending is not a way to cancel.
4. **Below the filled quantity** is rejected, not rounded up to it (ORD-1).
5. **Equal to the filled quantity** (with fills) is accepted and the order becomes `FILLED`, which is
   final (ORD-3, ORD-4). So a trader can close the unfilled rest this way, ending in `FILLED`, not `CANCELED`.
6. **Otherwise the status stays:** `NEW` stays `NEW`, `PARTIALLY_FILLED` stays `PARTIALLY_FILLED`.
7. **Same quantity** as now, on a working order, is accepted and changes nothing.
8. **NaN or infinite** `new_qty` is rejected.
9. **A rejected amend changes nothing.** An accepted one changes only `qty` and, in case 5, `status`.
   ID, side, limit price and fills stay. Later fills are checked against the new quantity.
10. **"Their place"** here means the same order object and ID. This code has no order book, queue or
    venue, so time priority is neither modeled nor promised. Some venues drop priority when size goes up.
11. **No amendment history:** `qty` is overwritten, and the previous quantity is not recorded.
12. **No new limits:** no maximum size or size of increase, lot step, margin or risk check, and no check
    of who may amend.
13. **No in-flight handling:** there is no pending or venue-confirmed state. The amend applies at once.
    After a reduction, a fill larger than the new remaining quantity is rejected by `apply_fill`, even if
    it was executed before the amend.
