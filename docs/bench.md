# FourEyes on someone else's code

10 bugs fixed in [python-humanize](https://github.com/python-humanize/humanize) in 2026, after the models' training data. For each: the code before the fix, the bug as a plain issue (symptom and example, no hint of the fix: [bench/issues](../bench/issues)), and the autopilot with nothing else. The maintainers' own regression tests were hidden from the factory and used only to judge.

| | |
|---|---|
| **Fixed** (the maintainers' hidden tests pass on the autopilot's code) | **8 of 10** |
| Blind tester's tests fail on the buggy code (would have caught it) | 9 of 10 |
| Author's own tests fail on the buggy code | 8 of 10 |
| Blind tests agree with the maintainers' fix | 4 of 10 |
| The gate passed | 6 of 10 |

| Bug | Fixed | Tester caught | Author caught | Tester agrees | Minutes | Cost |
|---|---|---|---|---|---|---|
| [#295](https://github.com/python-humanize/humanize/pull/295) naturaldelta-years | yes | yes | yes | yes | 2.6 | $3.27 |
| [#320](https://github.com/python-humanize/humanize/pull/320) fractional-negative | yes | yes | yes | yes | 3.8 | $3.01 |
| [#328](https://github.com/python-humanize/humanize/pull/328) metric-prefix | yes | yes | yes | no | 3.3 | $3.17 |
| [#329](https://github.com/python-humanize/humanize/pull/329) naturalsize-rollover | yes | yes | yes | no | 5.0 | $3.34 |
| [#334](https://github.com/python-humanize/humanize/pull/334) naturaldelta-inf | yes | yes | yes | no | 0.7 | $0.09 |
| [#346](https://github.com/python-humanize/humanize/pull/346) intword-carry | no | no | no | yes | ? | $0.00 |
| [#354](https://github.com/python-humanize/humanize/pull/354) fractional-whole | yes | yes | yes | yes | 3.1 | $2.81 |
| [#359](https://github.com/python-humanize/humanize/pull/359) metric-digits | yes | yes | yes | no | 3.9 | $2.83 |
| [#392](https://github.com/python-humanize/humanize/pull/392) intcomma-big-int | yes | yes | yes | no | ? | $0.00 |
| [#479](https://github.com/python-humanize/humanize/pull/479) far-future | no | yes | no | no | ? | $0.00 |

Total cost $18.52.
