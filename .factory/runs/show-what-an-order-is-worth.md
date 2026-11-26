## FourEyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Decide only these

Reply with one line per card, for example `/decide 1 keep`, or `/decide 1 <your own answer>`. Each answer becomes a blind test first, then code.

**1. Should a canceled order's notional include the unfilled quantity?**  
`src/orders/engine.py:36`: A canceled order still reports its full qty as notional (A5), so the risk team's exposure sums would count the unfilled remainder that can no longer trade, and no test can say whether that is what they want.
- `/decide 1 keep`: canceled orders report the full qty * limit_price
- `/decide 1 filled-only`: for CANCELED orders notional returns filled_notional (the canceled remainder counts as 0)
- `/decide 1 split`: keep notional as is and add a separate open_notional that is 0 for canceled orders

**2. Should the returned amounts be rounded to a fixed precision?**  
`src/orders/engine.py:42`: The result is an exact Decimal with no rounding (A3), and the limit checks and exports the risk team compares against may use a fixed number of decimals, so the sums could differ from theirs by sub-cent amounts.
- `/decide 2 keep`: exact Decimal, no rounding
- `/decide 2 round-2`: quantize to 2 decimals with ROUND_HALF_EVEN
- `/decide 2 round-per-fill`: quantize each fill's qty * price to 2 decimals before summing

> Adds two read-only functions, notional (qty * limit_price) and filled_notional (sum of fill qty * price), with no state changes; the money arithmetic is simple, but a few business choices (canceled orders, no rounding, no currency) need a person's confirmation.

### Tests

28 tests ran, 0 failed.

### Do the tests prove anything?

3 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 3 of 3 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 3 of 3 | yes |
| invariants | people (owned) | 0 of 3 | yes |
| **tester + invariants** | | **3 of 3** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 3 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/show-what-an-order-is-worth/tests/invariants/test_orders.py`. With it, the invariants catch **0 of 3**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/engine.py:34`: Mutation result: the invariants tests caught 0 of the 3 injected faults. The author and tester tests caught all 3, so the changed lines are covered, but the owned invariant tests do not constrain notional or filled_notional. The invariant tests only call them as read-only operations and check no value. This is acceptable because the invariants do not concern worth, but it means the formulas rely on the non-owned tests.
- **warn** `src/orders/engine.py:34`: Notional is a bare Decimal with no currency, and for a market-type order or a limit price of 0 it silently returns 0. If the platform trades in more than one currency, summing these values across orders would mix currencies.

### Provenance

- change: `02b94c28e4..362a4f043a`, 7 files
- requested by: Juicyscoop88; approver must be someone else
- agents that checked it: author (sonnet, $0.087), tester (opus, $0.201), author (sonnet, $0.052), tester (opus, $0.204), reviewer (sonnet, $0.030); total $0.574
- gate run: 2026-11-26 14:47 UTC

<!-- four-eyes-cards [{"where": "src/orders/engine.py:36", "why": "A canceled order still reports its full qty as notional (A5), so the risk team's exposure sums would count the unfilled remainder that can no longer trade, and no test can say whether that is what they want.", "question": "Should a canceled order's notional include the unfilled quantity?", "options": ["keep: canceled orders report the full qty * limit_price", "filled-only: for CANCELED orders notional returns filled_notional (the canceled remainder counts as 0)", "split: keep notional as is and add a separate open_notional that is 0 for canceled orders"], "id": "1"}, {"where": "src/orders/engine.py:42", "why": "The result is an exact Decimal with no rounding (A3), and the limit checks and exports the risk team compares against may use a fixed number of decimals, so the sums could differ from theirs by sub-cent amounts.", "question": "Should the returned amounts be rounded to a fixed precision?", "options": ["keep: exact Decimal, no rounding", "round-2: quantize to 2 decimals with ROUND_HALF_EVEN", "round-per-fill: quantize each fill's qty * price to 2 decimals before summing"], "id": "2"}] -->
