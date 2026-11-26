# Record why an order was canceled

Compliance asks why orders were canceled and we cannot tell. When an order is canceled we need to keep the reason: the trader, the risk system, or the venue. The reason must be set on every cancel and must not change afterwards.

## Interface

In `src/orders/model.py`, exported from `orders`:

```python
class CancelReason(Enum):
    TRADER = "trader"
    RISK_SYSTEM = "risk_system"
    VENUE = "venue"
```

`Order` gets one new field, last, with a default so existing construction keeps working:

```python
cancel_reason: CancelReason | None = None
```

In `src/orders/engine.py`, exported from `orders`:

```python
def cancel_with_reason(order: Order, reason: CancelReason) -> Order:
    """Cancel an order and record why. Raises OrderRejected if the order is
    already filled or canceled, or if reason is not a CancelReason.
    Sets status to CANCELED and cancel_reason to reason, together."""
```

## Assumptions

- **Existing `cancel(order)` is kept unchanged.** The owned invariant tests call it with one argument, so its signature cannot change without a person editing them. Consequence: `cancel(order)` still cancels with `cancel_reason = None`, so "set on every cancel" holds only for `cancel_with_reason`. A person decides whether `cancel` is later removed, deprecated, or made to require a reason.
- **Three reasons only**: trader, risk system, venue. No free text and no "other"/"unknown".
- **A missing or invalid reason is rejected** with `OrderRejected` and the order is left untouched (status and reason unchanged).
- **Cancel of a terminal order is rejected** as today (ORD-3), and the stored reason of an already canceled order is never overwritten, including by a second cancel with a different reason.
- **Immutability** is enforced by the engine (the only code path that sets it), not by freezing the `Order` dataclass. Direct attribute assignment is not guarded.
- **No timestamp, no actor id, no free-text note** are recorded; only the reason.
- **Reason is `None` until canceled**; only a canceled order has a reason (when canceled via `cancel_with_reason`).
