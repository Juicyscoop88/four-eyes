# Progress

## Done
- Task file `.factory/tasks/record-why-an-order-was-canceled.md` (interface, assumptions).
- Stubs: `CancelReason`, `Order.cancel_reason`, `cancel_with_reason` (raises NotImplementedError), exported.

## Next
- Tester writes blind tests from the task file; then implement `cancel_with_reason`.

## Open questions
- Keep, deprecate or change `cancel(order)` (owned tests call it without a reason)?
