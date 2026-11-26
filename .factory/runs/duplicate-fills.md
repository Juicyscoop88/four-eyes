## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Review map: decide only these

**1. Can this ship before the gateway and storage are ready, including for open orders whose fills have no id?**  
`src/orders/engine.py:41`: Duplicates are found only through ids stored on fills. A fill applied earlier through `apply_fill`, or reloaded without its `execution_id`, is applied again on redelivery if the order is still open and the quantity and price checks pass; the repo shows neither the gateway nor storage.
Answer with one: `ship: merge the engine change only. Gateway switch, storage of `execution_id` and handling of open orders stay outside this change, and the incident is not considered fixed by this merge.` · `gate: before release, require linked work that sends all venue reports through `apply_execution`, stores and reloads `Fill.execution_id`, and backfills or reconciles ids on open orders before any redelivery can reach them.`

**2. Is a plain `OrderRejected` enough for a conflicting redelivery?**  
`src/orders/engine.py:44`: A known id with a different quantity or price could be a venue correction or corrupted data. It raises the same `OrderRejected` type as an ordinary rejection, so callers get no distinct type for escalating a possible position mismatch; the task puts corrections out of scope but does not say how to escalate one.
Answer with one: `keep: raise plain `OrderRejected` with a message and leave the order unchanged.` · `distinct: raise an exported `ExecutionConflict(OrderRejected)` carrying the order id, execution id, applied values and received values, and leave the order unchanged.`

**3. Should at-most-once execution become an owned invariant?**  
`.factory/proposals/duplicate-fills/tests/invariants/test_orders.py:22`: The current invariant tests caught none of the 6 faults. The proposed replacement generates redeliveries but asserts only ORD-1 to ORD-4, none of which says that an execution is applied at most once; a double-applied partial fill within quantity and limit can satisfy all four. Only the invariant owners can change this.
Answer with one: `defer: add no new invariant. The proposal stays unadopted unless the owners apply it, and duplicate protection rests on the blind and unit tests.` · `add: the owners add ORD-5, 'an execution id is applied at most once per order', adopt the proposed tests, and add a property that redelivering an applied execution leaves status and fills unchanged and that non-null ids on an order's fills are unique.`

> The change adds `apply_execution`, which applies each execution id at most once per order; all 6 injected faults were caught by tester tests (0 by the current invariant tests), so your judgment is needed on rollout coverage, conflicting redeliveries and who guards the at-most-once rule.

### Tests

33 tests ran, 0 failed.

### Do the tests prove anything?

6 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 5 of 6 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 6 of 6 | yes |
| invariants | people (owned) | 0 of 6 | yes |
| **tester + invariants** | | **6 of 6** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 6 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/duplicate-fills/tests/invariants/test_orders.py`. With it, the invariants catch **1 of 6**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/engine.py:45`: As assumption 1 specifies, a duplicate returns the same order, just as a newly applied execution does. A gateway that books positions or publishes a fill event after each successful call could count the duplicate downstream. It would need to detect duplicates another way, for example by checking the order's fills before the call. No gateway code is in this repo to check.
- **warn** `src/orders/engine.py:43`: From reading the code (not run): redelivering an applied id with `Decimal("sNaN")` as quantity or price should raise `decimal.InvalidOperation` in this comparison instead of `OrderRejected`. The order stays unchanged, but a caller that catches only `OrderRejected` would not handle the error.

### Provenance

- change: `fc8174a9d4..c75f86f16e`, 9 files
- requested by: Jakub Schinko; approver must be someone else
- agents that checked it: author (sonnet, $0.164), tester (opus, $0.234), author (sonnet, $0.130), tester (opus, $0.190), reviewer (sonnet, $0.089); total $0.807
- gate run: 2026-11-26 13:23 UTC
