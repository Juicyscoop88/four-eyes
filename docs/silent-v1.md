# Silent failures: plain Claude Code, then FourEyes on its fix

Plain Claude Code (the author's model, the issue only, may run the tests) fixed each bug and said it was done. The maintainers' hidden tests judged the fix; FourEyes checked the same change as any pull request.

| | Gate blocked | Gate passed |
|---|---|---|
| **Fix wrong** (hidden tests fail) | **0 stopped** | 0 missed |
| Fix right | 5 false alarm | 5 passed |

Plain Claude Code's fix was wrong in 0 of 10 bugs, and said done every time.

| Bug | Fix right | Gate | Why it blocked |
|---|---|---|---|
| #295 naturaldelta-years | yes | blocked | 1 of the tester's tests fail |
| #320 fractional-negative | yes | passed | - |
| #328 metric-prefix | yes | blocked | 1 of the tester's tests fail |
| #329 naturalsize-rollover | yes | passed | - |
| #334 naturaldelta-inf | yes | passed | - |
| #346 intword-carry | yes | blocked | independent tests caught 5 of 7 injected faults, tier money needs 80% |
| #354 fractional-whole | yes | passed | - |
| #359 metric-digits | yes | passed | - |
| #392 intcomma-big-int | yes | blocked | reviewer at `src/humanize/number.py:179`: Input `intcomma(10**5000)` with CPython's default digit limit, on versions that enforce it: `f"{value:,}"` should rais |
| #479 far-future | yes | blocked | 6 of the tester's tests fail; reviewer at `src/humanize/time.py:65`: `precisedelta(timedelta(days=5000*365))` still raises `OverflowError: date value out of ran |

Total cost $3.65.
