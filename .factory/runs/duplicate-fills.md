## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Decide only these

Reply with one line per card, for example `/decide 1 keep`, or `/decide 1 <your own answer>`. Each answer becomes a blind test first, then code.

**1. Can this merge ship before the gateway uses apply_execution and storage persists Fill.execution_id?**  
`src/orders/engine.py:62`: Duplicates are detected only through execution_id stored on fills; fills applied via apply_fill or reloaded without an id are invisible, so their redelivery on an open order is applied twice, and no gateway or storage code in this repo shows that this does not happen.
- `/decide 1 ship`: merge the engine change only; gateway switch, id storage and open orders with id-less fills are tracked separately and the incident is not considered fixed by this merge.
- `/decide 1 gate`: block release until linked work routes all venue reports through apply_execution, persists and reloads Fill.execution_id, and reconciles open orders whose fills have no id.

**2. Is a silent, indistinguishable return for duplicates acceptable for the downstream callers?**  
`src/orders/engine.py:48`: A duplicate returns the same order object as a newly applied execution, so a caller that books positions or publishes events after every successful call would count the duplicate downstream; the spec fixes this behavior but a person must confirm the gateway can cope.
- `/decide 2 keep`: return the order unchanged as specified; the gateway checks order.fills for the id before calling if it needs to know.
- `/decide 2 flag`: add a helper or return marker, e.g. is_applied(order, execution_id), exported from orders, so callers can detect duplicates without inspecting fills.

**3. Should at-most-once execution become an owned invariant (ORD-5)?**  
`.factory/proposals/duplicate-fills/tests/invariants/test_orders.py:22`: ORD-1 to ORD-4 do not say an execution is applied at most once, and the current invariant tests caught 0 of the injected faults; a double-applied partial fill within quantity and limit satisfies all four, and only the invariant owners can change that.
- `/decide 3 defer`: add no invariant; duplicate protection rests on the blind and unit tests, and the proposal stays unadopted.
- `/decide 3 add`: add ORD-5 'an execution id is applied at most once per order', adopt the proposed tests, and add a property that redelivery leaves status and fills unchanged and non-null ids on an order's fills are unique.

> Adds apply_execution, which applies each venue execution id at most once per order and raises ExecutionConflict on a conflicting redelivery; the engine logic is small and well covered, but rollout coverage and the missing at-most-once invariant need a person.

### Tests

45 tests ran, 0 failed.

### Do the tests prove anything?

8 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 7 of 8 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 8 of 8 | yes |
| invariants | people (owned) | 0 of 8 | yes |
| **tester + invariants** | | **8 of 8** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 8 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/duplicate-fills/tests/invariants/test_orders.py`. With it, the invariants catch **3 of 8**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/engine.py:63`: Redelivering an applied id with Decimal('sNaN') as qty or price should make the tuple comparison raise decimal.InvalidOperation instead of OrderRejected or ExecutionConflict. The order stays unchanged, but a caller catching only OrderRejected would not handle it. Based on reading, not run.
- **warn** `src/orders/engine.py:67`: A new execution is applied through apply_fill and the id is attached afterward by replacing the last fill. This is correct for the current single-threaded flow, but if apply_fill ever stops appending exactly one fill, or concurrent delivery is introduced (out of scope per assumption 9), a fill could be recorded without its id and later be applied twice.

### Provenance

- change: `1f719c0929..c00c7a8b12`, 10 files
- requested by: Juicyscoop88; approver must be someone else
- agents that checked it: tester (opus, $0.138), author (sonnet, $0.089), reviewer (sonnet, $0.056); total $0.283
- gate run: 2026-11-26 13:59 UTC
