# Average fill price on the order

## Issue

Risk and client reporting both compute the average fill price themselves and they disagree on rounding.
Give the order one place that says it: the volume-weighted average price of its fills, none if it has no
fills yet. Report it to 6 decimal places, rounding half to even.

## Interface

A read-only property on `orders.Order` (`src/orders/model.py`), next to `filled_qty` and `remaining_qty`:

```python
@property
def average_fill_price(self) -> Decimal | None
```

`Order` is already exported from `orders`, so there is no new package export.

## Assumptions

1. **Form:** a property on `Order`, not a package function, because the issue asks for the order to say it.
2. **Formula:** `sum(qty * price) / sum(qty)` over `order.fills`. "None" means Python `None`, not zero.
3. **Rounding happens once:** fill quantities, prices and intermediate results are not rounded first. Only the
   final average is rounded, as if from the exact quotient, with `ROUND_HALF_EVEN`. An average just above or
   below a halfway point must not be turned into a tie by an earlier rounding.
4. **Caller's decimal context:** the caller's precision and rounding mode do not change the result, so all
   consumers get the same number. This also holds when inputs or the result have more digits than the
   caller's precision.
5. **Scale:** the result always has exactly 6 decimal places (`Decimal("100")` is reported as
   `100.000000`). It stays a `Decimal`, never a `float`. Display formatting is left to the consumer.
6. **Status:** the status does not matter. A canceled order with fills still has an average; one canceled
   without fills has `None`.
7. **Derived value:** it is computed from the current fills. It is not stored, and reading it changes nothing.
8. **Valid fills only:** fills have a finite price and a finite, positive quantity. This change adds no
   validation and defines nothing for other values put into `order.fills`.
9. **Scope:** `apply_fill`, the limit price and the stored fills do not change. Moving risk and client
   reporting to this property is not part of this task.
10. **Invariants:** no owned invariant in `invariants/orders.yaml` covers the average price or its rounding.
    This task does not edit the invariants. Adding one is the owners' decision.
