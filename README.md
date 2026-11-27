# FourEyes: a software factory prototype

> **People write issues. The factory does the rest, and nobody, human or agent, checks their own work.**

Try it: [docs/try-it.md](docs/try-it.md) · Design: [docs/design.md](docs/design.md) · Eval: [docs/eval.md](docs/eval.md) · Build log: [docs/build-log.md](docs/build-log.md)

## Three parts, each once

| Part | What | Where it runs |
|---|---|---|
| **The rule** | `foureyes check`: all suites, broken invariants named in words, faults injected into the changed lines and counted per suite (the author's own tests are measured, never counted), the reviewer's decision cards. Deterministic: the verdict never waits on a model. | CI, on every pull request |
| **The path** | `foureyes autopilot`: issue → plan → blind tests → code → gate → its own gaps closed → pull request with decision cards. `foureyes decide`: an answer becomes a blind test first, then code. Every step is a commit by its role. | CI (issue label, `/decide` comment) or a laptop (`/ship`) |
| **The guide** | Plugin `ftmo-factory`, arrives with the repo: hooks (no edits to owned files, no secrets, not done while an invariant is broken), `/ship`, and the factory's MCP: `rules_for(path)` (owners, tier, invariants, standards) and `why(path, line)` (issue, who asked, decisions, the tests that pin the line, approval). | Claude Code |

The roles, and what each may see:

| Role | Model | Sees | Never sees |
|---|---|---|---|
| author | Sonnet | the repo, under the hooks; `rules_for` | owned files as writable |
| tester | Opus (any model: isolation does the work, see the eval) | task, invariants, signatures | the implementation, the author's tests and chat |
| reviewer | Sonnet | task, diff, invariants, the gate's numbers; makes the decision cards (general bug review is Anthropic's `code-review`) | the author's conversation |

The tester is not a Claude Code subagent: a subagent shares the author's workspace. It runs in a copy of the
repo where every function body is `raise NotImplementedError`.

## On GitHub

| Workflow | When | What |
|---|---|---|
| `gate` | every pull request | the gate with the reviewer and gitleaks; the report and its cards as a comment by the CI bot. Bugs and CLAUDE.md: Anthropic's `code-review` plugin, inline comments (not rebuilt) |
| `autopilot` | an issue is labeled `autopilot` | the whole path, then a pull request |
| `decide` | someone with write access comments `/decide 1 reject` | the answer becomes a test, then code, then the gate again |

Real runs: issue #2 → PR #3, issue #4 → PR #5 (3.5 to 3.7 min, about $0.55 each); `/decide 2 distinct` on PR #1.
The gate is a command, so any CI runs it. Secret: `ANTHROPIC_API_KEY`, spend-limited (OIDC to a cloud is the
production design: no long-lived key).

## Run it locally

```bash
uv sync
uv run pytest                                  # the sample domain, invariants, blind tests, the gate's own tests
uv run foureyes autopilot issues/average-price.md  # the whole path on a branch (needs `claude` signed in)
uv run foureyes eval amend-quantity duplicate-fills average-price   # plant bugs, see what catches them
```

`factory.yaml` is the one file per repo: owned paths, invariants, standards, test suites, risk tiers, models.

## Limits

- 15 planted bugs is a small sample, and the adversary is also Claude.
- Hooks cover Claude Code's file tools; a shell command is stopped only by the gate in CI.
- Mutation scores saturate; planted bugs, not mutation, tell a good tester from a weak one.
- The reviewer misses things. It narrows a person's attention; approval stays human.
- Not built: OIDC, the paved road for non-engineers, a hosted MCP across repos.

Data is synthetic. Built mainly by directing Claude Code.
