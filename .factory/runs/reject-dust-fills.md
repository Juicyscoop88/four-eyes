## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Decide only these

Reply with one line per card, for example `/decide 1 keep`, or `/decide 1 <your own answer>`. Each answer becomes a blind test first, then code.

**1. Should an order whose min_fill_qty exceeds its total qty be allowed, and should a non-positive min_fill_qty be validated?**  
`src/orders/engine.py:14`: A minimum larger than the order's own qty, or a remainder that can never be reached (e.g. qty 10, min 5, after an 8 fill with 2 left), is accepted silently; the order can then only complete via an exact-remaining fill, so a venue sending slightly different partials leaves it stuck PARTIALLY_FILLED. Tests cannot decide whether this is acceptable.
- `/decide 1 keep`: no validation, as the task assumes; stuck-order risk accepted
- `/decide 1 reject`: raise ValueError in Order.__post_init__ when min_fill_qty is not None and (min_fill_qty <= 0 or min_fill_qty > qty)
- `/decide 1 clamp`: treat min_fill_qty above qty as qty in is_dust, leave non-positive as no minimum

> Adds an optional minimum fill size that rejects sub-minimum fills unless they equal the remaining quantity, placed after the existing checks; the logic is small and matches the task, so only one business edge case needs a person's judgment.

### Tests

30 tests ran, 0 failed.

### Do the tests prove anything?

5 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 5 of 5 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 5 of 5 | yes |
| invariants | people (owned) | 1 of 5 | yes |
| **tester + invariants** | | **5 of 5** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 1 of 5 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/reject-dust-fills/tests/invariants/test_orders.py`. With it, the invariants catch **1 of 5**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `.factory/proposals/reject-dust-fills/tests/invariants/test_orders.py:1`: The gate shows the invariants tests caught only 1 of 5 injected faults in the changed lines. The dust check itself is covered by author and tester tests, not by the invariant properties. The invariants appear safe here because the check only adds rejections before any state change, but this rests on reading the code, not on the invariant tests.
- **warn** `src/orders/engine.py:14`: is_dust compares with Decimal ordering and equality, so equal values with different exponents (5 vs 5.00) behave correctly. However, a venue fill with excess precision (e.g. 4.9999999) is rejected as dust with no log or metric, so rejected fills are silently dropped upstream unless the caller handles OrderRejected. Confirm the caller records the rejection.

### Provenance

- change: `96334800d5..0687ac9695`, 8 files
- requested by: Juicyscoop88; approver must be someone else
- agents that checked it: author (sonnet, $0.064), tester (opus, $0.163), author (sonnet, $0.054), tester (opus, $0.236), reviewer (sonnet, $0.029); total $0.546
- gate run: 2026-11-26 14:04 UTC

<!-- four-eyes-cards [{"where": "src/orders/engine.py:14", "why": "A minimum larger than the order's own qty, or a remainder that can never be reached (e.g. qty 10, min 5, after an 8 fill with 2 left), is accepted silently; the order can then only complete via an exact-remaining fill, so a venue sending slightly different partials leaves it stuck PARTIALLY_FILLED. Tests cannot decide whether this is acceptable.", "question": "Should an order whose min_fill_qty exceeds its total qty be allowed, and should a non-positive min_fill_qty be validated?", "options": ["keep: no validation, as the task assumes; stuck-order risk accepted", "reject: raise ValueError in Order.__post_init__ when min_fill_qty is not None and (min_fill_qty <= 0 or min_fill_qty > qty)", "clamp: treat min_fill_qty above qty as qty in is_dust, leave non-positive as no minimum"]}] -->
