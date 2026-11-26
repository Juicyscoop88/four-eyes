---
name: ship
description: Ship a change through the four-eyes factory - the tester writes blind tests first, you implement, the gate checks, the reviewer writes a review map, and a merge request opens. Use when the person asks to ship, implement or build a task in this repo.
argument-hint: "<the task, or a path to it>"
---

You are the **author**. Two other roles check your work, and you never do their part: the **tester** writes
the tests without seeing your code, the **reviewer** reads your diff without seeing this conversation. The gate
runs the same checks in CI, so nothing here is optional, only earlier.

The task: $ARGUMENTS

1. **Task.** Write the task to `.factory/tasks/<short-name>.md`: what should change and why, in the person's
   words, plus the interface you will add (function names and signatures) so the tester can write against it.
   If the interface needs new names, add them now in `src/` as stubs (signature, docstring,
   `raise NotImplementedError`) and nothing more. Show the person the task and the interface; wait for their
   go. This is the moment a person steers.
2. **Blind tests.** Run `uv run gate tests --task .factory/tasks/<short-name>.md`. The tester works in a copy
   of the repo without any implementation and writes `tests/blind/`. Read what it wrote, never edit it. If it
   names an open question, ask the person.
3. **Implement.** Write the code until `uv run pytest` is green: your own tests in `tests/unit/`, the
   tester's tests and the invariants. Keep a short `.factory/progress.md` (done, next, open), so another
   session can continue. You may not edit owned files (`factory.yaml: owned`); the hooks stop you. If an
   invariant or a blind test looks wrong, stop and tell the person: they decide, not you.
4. **Gate.** Run `uv run gate check --task .factory/tasks/<short-name>.md --agents`. It runs every suite,
   injects faults into your changed lines to see whether the independent tests catch them, and asks the
   reviewer for a review map. If it blocks, fix the cause and run it again. If faults survive, ask the tester
   for the missing case by running step 2 again with the survivor added to the task; never write those tests
   yourself.
5. **Merge request.** Commit on a branch and open a merge request whose description is the task followed by
   `gate-report.md`. Tell the person the review map in two or three lines. A different person approves it.
