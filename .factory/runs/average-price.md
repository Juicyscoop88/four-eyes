## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Review map: decide only these

**1. Should the owners adopt this proposed invariant test file?**  
`.factory/proposals/average-price/tests/invariants/test_orders.py:20`: Only the owners can change their invariant tests. This unapplied full-file proposal adds average-price reads to the random steps, but no invariant or assertion for the average's value or rounding. The diff doesn't show how it differs from the current owned file, so compare the two for weakened checks before adopting it.
Answer with one: `keep: leave it as an unapplied proposal; the owned invariants and their tests stay unchanged` · `adopt: after comparing it with the current file, the owners replace tests/invariants/test_orders.py with it, adding only the average-read step` · `extend: the owners add an invariant to invariants/orders.yaml for the exact VWAP, rounded once, half to even, to 6 places (None without fills), and add a matching assertion to this test before adopting it`

> This adds a read-only `Order.average_fill_price` that computes with exact fractions and rounds once, half to even. I found no blocking defect for realistic prices; a person mainly needs to decide on the proposed change to the people-owned invariant tests.

### Tests

27 tests ran, 0 failed.

### Do the tests prove anything?

1 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 1 of 1 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 1 of 1 | yes |
| invariants | people (owned) | 0 of 1 | yes |
| **tester + invariants** | | **1 of 1** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 1 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/average-price/tests/invariants/test_orders.py`. With it, the invariants catch **1 of 1**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/model.py:58`: On Python versions with the default 4300-digit limit for int-to-string conversion, formatting `millionths` raises ValueError if it exceeds that limit. For example, a directly stored fill with qty 1 and finite price Decimal('1E+4300') gets an error instead of an average. Extreme finite exponents such as 1E+100000000 or 1E-100000000 also make the Fraction arithmetic at line 55 build huge integers, which can make a read very slow or use a lot of memory. No realistic price is this large or small. `apply_fill` isn't in the diff, so I couldn't check whether it accepts such values. If it does, price magnitude and precision should be bounded where fills are accepted.
- **warn** `src/orders/model.py:55`: The property relies on every stored fill being valid. `Fraction` silently accepts a float and uses its exact binary value, which can change a half-even result compared with the intended decimal value. Fills whose quantities total zero raise ZeroDivisionError. The task leaves validation out of scope, and the diff doesn't show whether every path that creates or loads fills enforces Decimal values and positive quantities.

### Provenance

- change: `fc8174a9d4..7b2b7d5d73`, 7 files
- requested by: Jakub Schinko; approver must be someone else
- agents that checked it: author (sonnet, $0.116), tester (opus, $0.278), author (sonnet, $0.136), tester (opus, $0.153), reviewer (sonnet, $0.082); total $0.765
- gate run: 2026-11-26 13:27 UTC
