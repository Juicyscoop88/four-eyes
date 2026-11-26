# Progress: duplicate-fills

- Done: task and interface, blind tests, `apply_execution`, unit tests in `tests/unit/test_apply_execution.py`.
- Done: card 2, a conflicting redelivery raises exported `ExecutionConflict(OrderRejected)` with order id, execution id, applied and received values.
- Next: gate and review (the mutation score was not measured in the author session).
- Open: a person checks the assumptions, above all 4 (id scope) and 8 (`apply_fill` unguarded).
- Open: no owned invariant says an execution is applied at most once. The invariant owners decide whether to add it.
