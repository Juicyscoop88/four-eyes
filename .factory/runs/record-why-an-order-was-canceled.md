## Four Eyes gate

✅ **Passed.** A person approves the merge. Tier **money**.

### Decide only these

Reply with one line per card, for example `/decide 1 keep`, or `/decide 1 <your own answer>`. Each answer becomes a blind test first, then code.

**1. What should happen to the reason-less cancel(order)?**  
`src/orders/engine.py:30`: cancel(order) is unchanged and still produces a CANCELED order with cancel_reason None, so the requirement 'reason set on every cancel' is not met and compliance will still see unexplained cancels; the invariants tests (which have 0 mutation catches) call this path, so no test forces a decision.
- `/decide 1 keep`: leave cancel() as is, cancels without a reason remain possible
- `/decide 1 deprecate`: cancel() emits a DeprecationWarning and callers migrate to cancel_with_reason
- `/decide 1 require`: make cancel() take a mandatory reason and update the owned invariant tests to pass one

**2. Should the reason be protected against direct assignment, not just by the engine path?**  
`src/orders/engine.py:44`: Immutability of the reason relies only on cancel() rejecting terminal orders; Order is a mutable dataclass, so any code doing order.cancel_reason = x (or order.status = ...) bypasses it, and the compliance audit trail is only as strong as that convention.
- `/decide 2 keep`: engine-only enforcement, direct assignment unguarded
- `/decide 2 guard`: add __setattr__ on Order that raises if cancel_reason is already set to a different value
- `/decide 2 freeze`: make Order immutable and have the engine return replaced copies (larger change, touches all callers)

**3. Should the cancel-reason rule become an owned invariant with a property test?**  
`src/orders/model.py:24`: The mutation run injected 2 faults and the owned invariants tests caught 0 of them: the invariants (ORD-1..4) say nothing about cancel_reason, so nothing owned covers the new state. The rule 'only a canceled order has a reason, and a canceled one via this path always has one' is protected only by author and tester tests.
- `/decide 3 yes`: add an invariant (reason set iff canceled via cancel_with_reason, never changes once set) and a property test in the owned suite
- `/decide 3 no`: leave it covered by the author and tester tests only

> Adds a CancelReason enum, an Order.cancel_reason field and cancel_with_reason(), which validates the reason and then delegates to the unchanged cancel(); the logic is small and correct, but the plain cancel() path still leaves cancels without a reason, which is the main thing a person must decide.

### Tests

59 tests ran, 0 failed.

### Do the tests prove anything?

2 small faults were injected into the changed lines, one at a time.

| Tests | Written by | Caught | Counts |
|---|---|---|---|
| author | whoever wrote the code | 2 of 2 | no, nobody checks their own work |
| tester | the tester, who never saw the code | 2 of 2 | yes |
| invariants | people (owned) | 0 of 2 | yes |
| **tester + invariants** | | **2 of 2** (100%, needs 80%) | |

### For the owners of the invariants

The owned invariant tests caught 0 of 2 faults in this change: they do not exercise it yet. The tester (blind) proposes an extension in `.factory/proposals/record-why-an-order-was-canceled/tests/invariants/test_orders.py`. With it, the invariants catch **0 of 2**, and it passes on the current code. Only an owner can accept it.

### Reviewer findings

- **warn** `src/orders/model.py:24`: Unrelated formatting change `TERMINAL ={...}` (missing space before the brace) in a money-tier file; harmless at runtime but noise in the diff.
- **warn** `src/orders/engine.py:44`: Not a defect today: the reason is validated before cancel() runs, and cancel() raises on terminal orders before the reason is assigned, so rejected calls leave the order untouched. This ordering is not guarded by an owned test, so a refactor that sets the reason first would silently break it.

### Provenance

- change: `24d0215c2b..e15c9c2cba`, 8 files
- requested by: Juicyscoop88; approver must be someone else
- agents that checked it: author (sonnet, $0.096), tester (opus, $0.165), author (sonnet, $0.054), tester (opus, $0.139), reviewer (sonnet, $0.035); total $0.491
- gate run: 2026-11-26 14:12 UTC

<!-- four-eyes-cards [{"where": "src/orders/engine.py:30", "why": "cancel(order) is unchanged and still produces a CANCELED order with cancel_reason None, so the requirement 'reason set on every cancel' is not met and compliance will still see unexplained cancels; the invariants tests (which have 0 mutation catches) call this path, so no test forces a decision.", "question": "What should happen to the reason-less cancel(order)?", "options": ["keep: leave cancel() as is, cancels without a reason remain possible", "deprecate: cancel() emits a DeprecationWarning and callers migrate to cancel_with_reason", "require: make cancel() take a mandatory reason and update the owned invariant tests to pass one"]}, {"where": "src/orders/engine.py:44", "why": "Immutability of the reason relies only on cancel() rejecting terminal orders; Order is a mutable dataclass, so any code doing order.cancel_reason = x (or order.status = ...) bypasses it, and the compliance audit trail is only as strong as that convention.", "question": "Should the reason be protected against direct assignment, not just by the engine path?", "options": ["keep: engine-only enforcement, direct assignment unguarded", "guard: add __setattr__ on Order that raises if cancel_reason is already set to a different value", "freeze: make Order immutable and have the engine return replaced copies (larger change, touches all callers)"]}, {"where": "src/orders/model.py:24", "why": "The mutation run injected 2 faults and the owned invariants tests caught 0 of them: the invariants (ORD-1..4) say nothing about cancel_reason, so nothing owned covers the new state. The rule 'only a canceled order has a reason, and a canceled one via this path always has one' is protected only by author and tester tests.", "question": "Should the cancel-reason rule become an owned invariant with a property test?", "options": ["yes: add an invariant (reason set iff canceled via cancel_with_reason, never changes once set) and a property test in the owned suite", "no: leave it covered by the author and tester tests only"]}] -->
