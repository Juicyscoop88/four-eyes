# Money in code

- Quantities and prices are `Decimal`, never `float`. Rounding is explicit, with its mode named.
- A state change happens after every check passed, never before.
- Every rejection is an `OrderRejected` (or a subclass) with a reason a person can read.
