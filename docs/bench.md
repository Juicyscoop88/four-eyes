# FourEyes on someone else's code

1 bugs fixed in [python-humanize](https://github.com/python-humanize/humanize) in 2026, after the models' training data. For each: the code before the fix, the bug as a plain issue (symptom and example, no hint of the fix: [bench/issues](../bench/issues)), and the autopilot with nothing else. The maintainers' own regression tests were hidden from the factory and used only to judge.

| | |
|---|---|
| **Fixed** (the maintainers' hidden tests pass on the autopilot's code) | **1 of 1** |
| Blind tester's tests fail on the buggy code (would have caught it) | 1 of 1 |
| Author's own tests fail on the buggy code | 1 of 1 |
| Blind tests agree with the maintainers' fix | 0 of 1 |
| The gate passed | 0 of 1 |

| Bug | Fixed | Tester caught | Author caught | Tester agrees | Minutes | Cost |
|---|---|---|---|---|---|---|
| [#334](https://github.com/python-humanize/humanize/pull/334) naturaldelta-inf | yes | yes | yes | no | ? | $0.00 |

Total cost $0.00.
