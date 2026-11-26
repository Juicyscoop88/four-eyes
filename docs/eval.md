# Eval: planted bugs and tester models

3 tasks done by the autopilot, 15 realistic bugs planted by an adversary agent that saw the finished code (invalid edits excluded). Each bug ran against every suite.

| Check | Bugs caught |
|---|---|
| author's own tests | 5 of 15 |
| tester on haiku (blind) | 13 of 15 |
| tester on sonnet (blind) | 15 of 15 |
| tester on opus (blind) | 14 of 15 |
| owned invariants | 0 of 15 |
| owned invariants with the tester's proposal | 2 of 15 |
| **the gate's tests** (factory tester + invariants) | **14 of 15** |
| reviewer, on the bugs no test caught | 1 of 1 |

## Tester models, by mutation on the changed lines

| Task | haiku | sonnet | opus |
|---|---|---|---|
| amend-quantity | 11 of 11 | 11 of 11 | 11 of 11 |
| duplicate-fills | 8 of 8 | 8 of 8 | 8 of 8 |
| average-price | 7 of 7 | 7 of 7 | 7 of 7 |

## What the gate's tests missed

- **average-price**, `src/orders/model.py`: filled_qty adds Decimals in the caller's context. With prec=3 and fill quantities such as 1000 and 1, the denominator is rounded and the average is wrong. (the reviewer blocked it)

Cost of the eval: $0.66.
