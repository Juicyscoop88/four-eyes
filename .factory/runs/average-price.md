## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Review map: decide only these

**1. Should the average fill price and its rounding become an owned invariant?**  
`.factory/proposals/average-price/tests/invariants/test_orders.py:19`: No owned invariant covers the average or its rounding, and the owned tests caught 0 of 7 faults. The proposed file reads the average but never asserts its value, so adopting it would not detect a wrong price or rounding mode, and only the owners can decide what to guarantee to risk and client reporting.
Answer with one: `keep: leave invariants/orders.yaml and the owned tests unchanged and the proposal unapplied, so only the non-owned tests check the value` · `extend: the owners add an invariant (exact VWAP of the fills, rounded once, half to even, to 6 places, None without fills) and a property test in tests/invariants/test_orders.py that compares the result with an independent exact calculation` · `reads-only: after comparing the proposal with the current owned test file to rule out weakened checks, the owners adopt it as a check that random average reads don't break ORD-1 to ORD-4, not as a check of the value`

> Adds a read-only `Order.average_fill_price` that uses exact fractions and rounds once, half to even, to 6 places. All 7 injected faults were caught by the tester's tests and I found no blocking defect, so the main decision is whether this number gets owned protection.

### Tests

27 tests ran, 0 failed.

### Do the tests prove anything?

7 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 7 of 7 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 7 of 7 | yes |
| invariants | people (owned) | 0 of 7 | yes |
| **tester + invariants** | | **7 of 7** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 7 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/average-price/tests/invariants/test_orders.py`. With it, the invariants catch **2 of 7**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/model.py:57`: With Python's default 4300-digit limit on int-to-string conversion, a finite fill with qty 1 and price Decimal('1E+4300') should raise ValueError here instead of returning an average. Extreme exponents such as 1E+100000000 or 1E-100000000 can also make the Fraction arithmetic very slow or memory-hungry. These are not realistic prices, so I don't block on them. `apply_fill` is not in the diff, so I couldn't check whether it accepts them. If it does, bound price and quantity magnitude and precision where fills are accepted.
- **warn** `.factory/runs/average-price.json:6`: The committed run record reports 1 injected fault (author 1, tester 1, invariants 0, proposal 0 to 1). The measurement supplied for this review has 7 faults (author 7, tester 7, invariants 0). Don't use the committed record, or its claim about what the proposal catches, as evidence for this change unless you can tie it to the exact revision and gate run. The diff doesn't explain the mismatch.

### Provenance

- change: `8c8f9d30a1..c6ce811b04`, 9 files
- requested by: Jakub Schinko; approver must be someone else
- agents that checked it: reviewer (sonnet, $0.090); total $0.090
- gate run: 2026-11-26 13:29 UTC
