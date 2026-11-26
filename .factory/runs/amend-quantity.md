## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Review map: decide only these

**1. Should an amend down to exactly the filled quantity end the order as FILLED?**  
`src/orders/engine.py:49`: Reducing to the filled quantity ends the order permanently as FILLED, so a trader who gave up the unfilled rest is reported to the client and regulator as fully filled at a smaller size, and tests can only confirm the assumed rule, not that this reporting is right.
Answer with one: `keep: accept it and set the status to FILLED` · `reject: raise OrderRejected when new_qty <= filled_qty on an order with fills, so the trader must use cancel` · `cancel: accept it, leave qty unchanged and set the status to CANCELED, keeping the fills`

**2. May a reduction take effect before the venue confirms it?**  
`src/orders/engine.py:47`: A reduction applies immediately with no pending or confirmed state, so `apply_fill` rejects a fill that was already executed but arrives late if it exceeds the new remaining quantity, which could leave a real position unrecorded.
Answer with one: `keep: apply it at once and let apply_fill reject any late fill that no longer fits` · `block-reductions: raise OrderRejected for any new_qty below the current qty until in-flight handling exists`

**3. May this function increase an order's size without a limit or risk check?**  
`src/orders/engine.py:47`: Any finite increase is accepted with no maximum or risk check and keeps the same order, and the owned invariants only limit fills to whatever the new quantity is. This diff does not show whether order entry or another layer enforces such limits.
Answer with one: `keep: accept any finite increase, with limits and authorization handled elsewhere or not at all` · `reductions-only: raise OrderRejected when new_qty > qty until a risk check exists`

> Adds in-place `amend_quantity`; I found no concrete defect in the engine change, but a person should decide three business rules, and the owned invariant tests caught none of the 9 injected faults.

### Tests

56 tests ran, 0 failed.

### Do the tests prove anything?

9 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 7 of 9 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 9 of 9 | yes |
| invariants | people (owned) | 0 of 9 | yes |
| **tester + invariants** | | **9 of 9** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 9 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/amend-quantity/tests/invariants/test_orders.py`. With it, the invariants catch **6 of 9**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `.factory/proposals/amend-quantity/tests/invariants/test_orders.py:35`: The proposed ORD-3 test snapshots only status and fills, not qty. If an amend changed the qty of a CANCELED order, the status and fills would stay the same. The ORD-4 test skips CANCELED orders, and ORD-1 would miss any new qty at or above the filled quantity. Include qty (and limit_price) in the terminal snapshot before the owners adopt the proposal.
- **warn** `src/orders/engine.py:28`: The owned invariant tests caught 0 of the 9 injected faults. The progress note says they do not call amend_quantity, and the updated version is only a proposal under .factory/proposals. Until an owner reviews and adopts it, the owned suite does not check ORD-1, ORD-3 or ORD-4 against amends.
- **warn** `src/orders/engine.py:47`: qty is overwritten and the previous value is not recorded (assumption 11). Unless something outside this diff records amendments, the order cannot show its earlier size or that a FILLED status came from a reduction. Whoever owns the regulatory audit trail should confirm where this is recorded.
- **warn** `src/orders/engine.py:47`: The task asks that traders not lose their place, but only the object and ID are preserved. Time priority is not modeled, and some venues drop it when size increases (assumption 10). Do not present this change to traders as guaranteeing queue priority.

### Provenance

- change: `fc8174a9d4..c264abe739`, 8 files
- requested by: Jakub Schinko; approver must be someone else
- agents that checked it: author (sonnet, $0.137), tester (opus, $0.235), author (sonnet, $0.119), tester (opus, $0.185), reviewer (sonnet, $0.085); total $0.762
- gate run: 2026-11-26 13:19 UTC
