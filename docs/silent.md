# Silent failures: plain Claude Code, then FourEyes on its fix

Plain Claude Code (the author's model, the issue only, may run the tests) fixed each bug and said it was done. The maintainers' hidden tests judged the fix; FourEyes checked the same change as any pull request.

| | Gate blocked | Gate passed |
|---|---|---|
| **Fix wrong** (hidden tests fail) | **0 stopped** | 0 missed |
| Fix right | 2 false alarm | 8 passed |

Plain Claude Code's fix was wrong in 0 of 10 bugs, and said done every time.

| Bug | Fix right | Gate | Why it blocked |
|---|---|---|---|
| #295 naturaldelta-years | yes | passed | - |
| #320 fractional-negative | yes | passed | - |
| #328 metric-prefix | yes | passed | - |
| #329 naturalsize-rollover | yes | blocked | 1 of the tester's tests fail |
| #334 naturaldelta-inf | yes | passed | - |
| #346 intword-carry | yes | passed | - |
| #354 fractional-whole | yes | passed | - |
| #359 metric-digits | yes | passed | - |
| #392 intcomma-big-int | yes | passed | - |
| #479 far-future | yes | blocked | 5 of the tester's tests fail; reviewer at `src/humanize/time.py:64`: A large timedelta such as `precisedelta(datetime(9999, 12, 31) - datetime(2026, 11, 27))` s |

Total cost $3.56.
