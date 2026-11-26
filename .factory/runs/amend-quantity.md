## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Decide only these

Reply with one line per card, for example `/decide 1 keep`, or `/decide 1 <your own answer>`. Each answer becomes a blind test first, then code.

**1. May a reduction take effect before the venue confirms it?**  
`src/orders/engine.py:47`: A reduction applies at once with no pending or confirmed state, so `apply_fill` will reject an already executed fill that arrives late and exceeds the new remaining quantity (assumption 13), possibly leaving a real position unrecorded.
- `/decide 1 keep`: apply it at once and let apply_fill reject any late fill that no longer fits
- `/decide 1 block`: raise OrderRejected for any new_qty below the current qty until in-flight handling exists

**2. May an order's size be increased here without a limit or risk check?**  
`src/orders/engine.py:47`: This function accepts any finite increase above the filled quantity with no maximum, risk or authorization check. The owned invariants only cap fills at the new quantity, and the diff does not show whether another layer enforces limits.
- `/decide 2 keep`: accept any finite increase, with any limits and authorization left outside this function
- `/decide 2 reductions-only`: raise OrderRejected when new_qty > order.qty until a risk check exists

> Adds in-place `amend_quantity`, and I found no concrete defect in the engine change. It matches the recorded decision to reject `new_qty <= filled_qty`, but a person still needs to decide how reductions treat late fills and whether increases may go unchecked.

### Tests

60 tests ran, 0 failed.

### Do the tests prove anything?

7 small faults were injected into the changed lines, one at a time (2 more changed no behavior, see below).

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 6 of 7 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 7 of 7 | yes |
| invariants | people (owned) | 0 of 7 | yes |
| **tester + invariants** | | **7 of 7** (100%, needs 80%) | |

<details><summary>Faults judged equivalent by the reviewer (not counted)</summary>

- M6 `src/orders/engine.py:42` `<=` became `<`: The fault only changes how an amendment to exactly zero passes the positive-quantity check. The later rule rejects any new total that is not above the filled quantity. The filled quantity is never below zero, so zero is still rejected with the same kind of rejection and the order is unchanged. This holds for orders with and without fills, and terminal orders are rejected earlier. Only the wording of the rejection message differs, and the task does not specify it. This assumes fills always have positive quantities. The diff does not show the fill-handling code that enforces this, and an order built by hand with a negative fill total is not treated as a valid input.
- M7 `src/orders/engine.py:43` a `raise` was removed (a guard that no longer guards): Without the positive-quantity rejection, a zero or negative new total reaches the rule that rejects any total not above the filled quantity. The filled quantity is never below zero, so every such input is still rejected with the same kind of rejection and nothing on the order changes. Non-finite values and terminal orders are rejected before this point. Only the wording of the rejection message differs, and the task does not specify it. This relies on the same assumption as M6: fills always have positive quantities, which the diff does not show. The existing tests for zero and negative totals already check the behaviour the task requires.

</details>

### For the owners of the invariants

The owned invariant tests caught 0 of 7 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/amend-quantity/tests/invariants/test_orders.py`. With it, the invariants catch **2 of 7**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/engine.py:47`: `order.qty` is overwritten and the previous value is not recorded (assumption 11). The diff shows no other amendment record, so the audit trail owner should confirm that earlier sizes are recorded elsewhere.
- **warn** `src/orders/engine.py:47`: Only the order object and ID keep their "place". Queue or time priority is not modeled, and some venues drop it when size increases (assumption 10), so traders should not be told it is preserved.
- **warn** `src/orders/engine.py:28`: The owned invariant tests caught 0 of the 7 injected faults, and the extended version is only a proposal under `.factory/proposals`. The diff does not add it to the owned suite, so an owner needs to review and adopt it for that suite to cover amends.
- **warn** `.factory/proposals/amend-quantity/tests/invariants/test_orders.py:36`: The ORD-3 snapshot holds only status and fills. A faulty amend that changed `qty` on a CANCELED order would pass that test, and the ORD-4 test skips CANCELED orders. Add `qty` and `limit_price` to the snapshot and its assertion before adopting the proposal.
- **warn** `.factory/runs/amend-quantity.md:9`: The committed run report and its JSON do not match the current gate results. They report 9 faults (the current run has 7) and 56 tests (now 60). They still ask the already decided FILLED question, with "keep" meaning accept and set FILLED, and the proposal's 6 of 9 score comes from that run. An approver should not rely on them for this version; regenerate them or label them as superseded.
- **warn** `.factory/tasks/amend-quantity.md:25`: Assumption 5 still says an amend to the filled quantity is accepted and sets FILLED. The Decisions section and the code reject it. Update the assumption, along with the reference to "case 5" in assumption 9, so nobody implements or tests the old rule.

### Provenance

- change: `8fd1e6d5e1..afd4251f0a`, 9 files
- requested by: Jakub Schinko; approver must be someone else
- agents that checked it: tester (opus, $0.188), author (sonnet, $0.138), reviewer (sonnet, $0.084), reviewer (sonnet, $0.097); total $0.507
- gate run: 2026-11-26 13:53 UTC
