# Progress

## Done
- Task `reject-dust-fills`: spec and assumptions in `.factory/tasks/reject-dust-fills.md`; stub `is_dust` and field `Order.min_fill_qty` added.

## Next
- Tester writes blind tests from the task file; then implement `is_dust` and the check in `apply_fill`.

## Open questions
- See Assumptions in the task file (e.g. non-positive minimum is not validated).
