# Amend quantity: progress

- Done: task and assumptions (`.factory/tasks/amend-quantity.md`); blind tests (`tests/blind/`); `amend_quantity` in `src/orders/engine.py`; author tests in `tests/unit/`. `uv run pytest`: 62 passed.
- Next: gate and review (not run in the author session).
- Open (person): assumptions 5, 10 and 13. The owned property tests do not drive `amend_quantity`.
