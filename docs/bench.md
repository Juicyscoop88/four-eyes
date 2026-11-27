# FourEyes on someone else's code

10 bugs fixed in [python-humanize](https://github.com/python-humanize/humanize) in 2026, after the models' training data. For each: the code before the fix, the bug as a plain issue (symptom and example, no hint of the fix: [bench/issues](../bench/issues)), and the autopilot with nothing else. The maintainers' own regression tests were hidden from the factory and used only to judge.

| | |
|---|---|
| **Fixed** (the maintainers' hidden tests pass on the autopilot's code) | **9 of 10** |
| Blind tester's tests fail on the buggy code (would have caught it) | 10 of 10 |
| Author's own tests fail on the buggy code | 10 of 10 |
| Blind tests agree with the maintainers' fix | 3 of 10 |
| The gate passed | 9 of 10 |

| Bug | Fixed | Tester caught | Author caught | Tester agrees | Minutes | Cost |
|---|---|---|---|---|---|---|
| [#295](https://github.com/python-humanize/humanize/pull/295) naturaldelta-years | yes | yes | yes | yes | 2.6 | $3.27 |
| [#320](https://github.com/python-humanize/humanize/pull/320) fractional-negative | yes | yes | yes | yes | 3.8 | $3.01 |
| [#328](https://github.com/python-humanize/humanize/pull/328) metric-prefix | yes | yes | yes | no | 3.3 | $3.17 |
| [#329](https://github.com/python-humanize/humanize/pull/329) naturalsize-rollover | yes | yes | yes | no | 5.0 | $3.34 |
| [#334](https://github.com/python-humanize/humanize/pull/334) naturaldelta-inf | yes | yes | yes | no | 2.2 | $0.52 |
| [#346](https://github.com/python-humanize/humanize/pull/346) intword-carry | yes | yes | yes | no | 2.8 | $0.58 |
| [#354](https://github.com/python-humanize/humanize/pull/354) fractional-whole | yes | yes | yes | yes | 3.1 | $2.81 |
| [#359](https://github.com/python-humanize/humanize/pull/359) metric-digits | yes | yes | yes | no | 3.9 | $2.83 |
| [#392](https://github.com/python-humanize/humanize/pull/392) intcomma-big-int | yes | yes | yes | no | 2.9 | $0.62 |
| [#479](https://github.com/python-humanize/humanize/pull/479) far-future | no | yes | yes | no | 6.4 | $1.55 |

Total cost $21.70.

## What it taught us

- **No wrong fix passed the gate.** #479 is the one bug not fixed. The gate blocked it and asked a person three
  questions (thousands separator, `minimum_unit`, year rounding), and the maintainers' hidden tests confirm the
  code was not right yet. A factory that stops and asks is the behavior we want.
- **Hermetic agents are about five times cheaper.** The first runs cost about $3 a bug: the author loaded every MCP
  server of the laptop it ran on (339 tools from 11 servers). With only the servers `factory.yaml` names, the same
  kind of bug costs $0.52 to $0.62 (#334, #346, #392). The rows above $2.80 are from before the change.
- **"Tester agrees" is low on purpose.** The blind tester writes expectations for edge cases the issue leaves open.
  Where they differ from the maintainers' later choice, they are questions for a person, not bugs.
- **Found by the bench, fixed in the factory:** the plan must write its task (it once wrote none), and a rerun
  starts from a fresh branch.

