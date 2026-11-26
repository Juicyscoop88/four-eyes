# Four Eyes: a software factory prototype

**Nobody, human or agent, checks their own work.** The prototype is the narrow slice of the design in
[docs/design.md](docs/design.md) that shows the idea: one change goes from a task to a gated merge request,
and every check on the way is done by someone who did not write the code.

```
task (person)  ──►  tester writes blind tests  ──►  author implements  ──►  gate  ──►  merge request + review map  ──►  person approves
                    (never sees the code)           (person or agent)       (CI)
```

## What runs

| Part | Where | What it does |
|---|---|---|
| `factory.yaml` | repo root | The one file per repo: owned paths, the three test suites, risk tiers by path. |
| `gate tests` | `tools/gate/agents.py` | Runs the **tester** (headless Claude Code) in a copy of the repo where every function body is replaced by `raise NotImplementedError` and the author's tests are deleted. It writes `tests/blind/`. Isolation is physical, not a prompt. |
| `gate check` | `tools/gate/check.py` | Runs all suites, names a broken invariant in words, **mutation-tests the changed lines** and counts per suite which injected faults were caught (the author's own tests are measured but do not count), and asks the **reviewer** (headless, empty workspace, sees only task, diff, invariants and the gate's numbers) for a review map of at most three places. Writes `gate-report.md`, the merge request comment. |
| Plugin `four-eyes` | `plugin/` | Arrives with the repo (`.claude/settings.json` lists it). Hooks: an agent never edits an owned file and never writes a secret (PreToolUse); an agent that changed code is not done while an invariant is broken (Stop). Skill `/ship` walks the author through the whole path. |
| CI | `.gitlab-ci.yml` | The same `gate check --agents` on every merge request, beside GitLab's own Secret Detection and SAST. The report is posted by the factory's bot account, not an engineer's. |

Why the tester is not a Claude Code subagent: a subagent runs in the author's workspace and can read the
code. Only a separate workspace without the code makes "the tester never saw it" true.

## On GitHub

| Workflow | When | What |
|---|---|---|
| `gate` | every pull request | the gate with the reviewer; the report and its decision cards as a comment |
| `autopilot` | an issue gets the label `autopilot` | plan, blind tests, code, gate, a pull request |
| `decide` | someone with write access comments `/decide 1 reject` | the answer becomes a blind test, then code, then the gate again |

The same gate runs on GitLab (`.gitlab-ci.yml`). Secret: `ANTHROPIC_API_KEY`, spend-limited, used only by CI.

## Run it

```bash
uv sync
uv run pytest                     # the sample domain, the invariants, the gate's own tests
scripts/demo.sh                   # the demo, step by step (needs `claude` signed in for the last step)
```

On any branch:

```bash
uv run gate tests --task .factory/tasks/<task>.md        # the tester writes blind tests
uv run gate check --base main --task <task> --agents     # the gate, with the reviewer
```

## The demo (branch `demo/amend`)

The task: amend the quantity of an open order.

1. The tester wrote 18 tests without seeing any implementation, from the task and the invariants.
2. The author's first try (`demo/1-rushed`, seeded for the demo) forgets that an order may already be
   partly filled. Its own tests are green. **The gate blocks it:** 8 of the tester's tests fail
   (amend below the filled quantity, amend to exactly the filled quantity).
3. After the fix, the reviewer **blocked on a real gap nobody seeded**: `Decimal("Infinity")` passed every
   check. The person decided that a quantity must be finite, the tester added the tests (blind again), the
   author fixed it.
4. The gate passes: tester's tests caught 9 of 9 injected faults, the author's own 6 of 9, the owned
   invariants 0 of 9 (they do not cover amend yet, and the reviewer said so). The review map names three
   decisions for a person, all business choices no test can settle. Cost of the checks: about $0.16.

## Limits

- The hooks cover Claude Code's file tools. A shell command that writes an owned file is not stopped
  locally; the gate in CI blocks it for everyone.
- Mutation testing uses a few operators (comparisons, `+`/`-`, `and`/`or`, `not`, removed `raise`) on the
  changed lines only. It finds weak tests, not every weak test.
- The reviewer misses things. It narrows a person's attention; it does not replace the approval.
- The tester depends on a clear interface. Here the author writes the signatures first, as stubs.
- Not built: shadow agent, signed provenance, the run over past merge requests, the paved road for
  non-engineers. They are in the design.

Data is synthetic. Built mainly by directing Claude Code: see [docs/build-log.md](docs/build-log.md).
