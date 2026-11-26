# Amend quantity: progress

- Done: task and assumptions (`.factory/tasks/amend-quantity.md`); blind tests (`tests/blind/`); `amend_quantity` in `src/orders/engine.py`; author tests in `tests/unit/`.
- Done: card 1 decision applied (Jakub Schinko): `new_qty <= filled_qty` is rejected, so an amend never ends an order.
- Next: gate and review of this change (not run in the author session).
- Open (person): assumptions 10 and 13. The owned property tests do not drive `amend_quantity`. Assumption 5 in the task file still states the old behavior; the Decisions section overrides it.
