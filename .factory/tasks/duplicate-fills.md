# Fills counted twice after a redelivery

Last week the venue gateway redelivered execution reports after a reconnect and some fills were applied
twice. Every execution report has an execution id from the venue. Applying the same execution twice must
not change the order a second time. Different executions of the same order are still all applied.

## Interface

New function in `src/orders/engine.py`, exported from `orders`:

```python
def apply_execution(order: Order, execution_id: str, qty: Decimal, price: Decimal) -> Order:
```

New last field of `Fill` in `src/orders/model.py`:

```python
execution_id: str | None = None
```

`apply_fill` and `cancel` keep their signatures and behavior.

## Assumptions

1. **A redelivery is not an error.** The same id with equal `qty` and `price` returns the order unchanged,
   without raising. The return value does not tell the caller that it was a duplicate.
2. **This also holds on a finished order.** Redelivery of an applied execution to a filled or canceled
   order (for example the fill that completed it) returns it unchanged. So the duplicate check comes before
   the status, quantity and limit price checks.
3. **Same id, different content is rejected.** If `qty` or `price` differs from the applied execution,
   `OrderRejected` is raised and the order does not change. Values are compared as numbers
   (`Decimal("100")` equals `Decimal("100.0")`).
4. **An id identifies an execution within one order.** The same id on two different orders is applied to
   both. There is no check across orders. Ids are compared exactly (case and whitespace count).
5. **An empty id is rejected** with `OrderRejected`.
6. **Only applied executions are remembered.** A rejected report leaves no trace, so its redelivery is
   checked again as new.
7. **New executions follow the existing rules.** A new id is rejected in the same cases as in `apply_fill`,
   including any new execution on a filled or canceled order. Two different ids with equal `qty` and
   `price` are two executions.
8. **`apply_fill` stays, without duplicate protection.** The owned invariant tests call it without an id.
   Venue execution reports must go through `apply_execution`. This repo contains no gateway code that calls
   either one, so switching the gateway over is not part of this change.
9. **The ids live on the order's fills.** Protection survives a restart only if whatever stores the order
   also stores `Fill.execution_id`. Storage and concurrent delivery are out of scope.
10. **Out of scope:** repairing orders that already counted a fill twice, and venue corrections or busts of
    an earlier execution.
