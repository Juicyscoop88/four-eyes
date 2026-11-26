# FTMO & OANDA case study: Design Your Software Factory

Take-home for the AI Engineer role (Hiring Sprint #1). Brief: [brief.md](brief.md). Due Tue 2026-12-01, presented in Prague Thu 12-03 or Fri 12-04 (35 to 40 min plus discussion). Working notes: [docs/thinking.md](docs/thinking.md), [docs/use-cases.md](docs/use-cases.md).

## The idea in one line

**Four eyes for agents.** We do not change how anyone writes code. We change what every change must prove before it merges, and nobody, human or agent, checks their own work.

## People write issues, the factory does the rest

**Autopilot by default, the wheel always within reach.** A person writes the issue (what and why). The factory
takes it from there on its own: plan, blind tests, code, gate, closing its own gaps, merge request. A person
is asked only for what only a person can decide, as decision cards in the merge request, answered in a word.
Anyone can take the wheel at any step (check out the branch, go on by hand, the factory keeps testing and
reviewing) and hand it back ("finish it"). Opting out is a label, not a setup.

- **The factory closes its own gaps:** faults no independent test caught go back to the tester (blind
  again) until the tier's score is met; when the owned invariants do not cover new code, an agent proposes
  the extension as a merge request to their owners.
- **Decision cards:** each point of the review map is a thread in the merge request with a few answers; the
  answer becomes a change, tested and gated again. The merge request is the whole interface.
- **Free tests for people:** a person who writes by hand gets blind tests and a review map on their merge
  request. Four eyes works both ways.
- **Custom without a fork:** `factory.yaml` per repo, the team's own skills, each person's own CLAUDE.md.

## Where we sit on their range

In the middle, on purpose. A person decides at the start (what and why) and at the end (merge). Everything between is automated. The author may be a person or an agent; the factory does not care.

## The minimal system

1. **One rule:** four eyes. Author, tester and reviewer are always different contexts.
   - author writes the code (person or agent);
   - tester sees only the task and the invariants, never the author's code or reasoning;
   - reviewer sees the diff and the task, never the author's chat.
2. **One place:** the merge request. The factory ends at merge; deploy and environments stay theirs.
3. **One file per repo:** what is an invariant (owned by people) and what is risky (risk tiers by path).

Everything else is what they already have: GitLab, Claude Code, Claude on Vertex AI, Grafana. We do not build what exists.

## Three parts, each once (keep it light)

1. **The rule:** `foureyes check` in CI, deterministic. Code decides; a model never gives the verdict.
2. **The path:** `foureyes autopilot` (issue → plan → blind tests → code → gate → gaps closed → pull request with
   decision cards) and `foureyes decide` (an answer becomes a blind test, then code). CI from an issue label and
   `/decide` comments; a laptop through `/ship`. One path, not two.
3. **The guide:** plugin `four-eyes` (arrives with the repo): hooks, `/ship`, FourEyes MCP with `rules_for`
   and `why`. MCP is for people and agents in Claude; CLI is only for what has no chat (CI, the eval).

Nothing exists twice. Before adding a surface, ask whether an existing one already does it.

## This repo

```
factory.yaml             owned paths, invariants, standards, suites, risk tiers, models per role
invariants/orders.yaml   owned invariants of the sample domain (with the paths they hold for)
standards/               how things are done here: design system, optimistic UI, money
src/orders/              synthetic order handling: the code the factory protects
tests/invariants/        property tests that prove the invariants (owned like them)
tests/blind/             the tester's tests, written without seeing the code
tests/unit/              the author's own tests (measured, never counted)
tests/foureyes/          tests of the factory itself
tools/foureyes/          the CLI `foureyes`: the gate, autopilot, roles, MCP, eval (owned)
plugin/                  the Claude Code plugin: roles, hooks, /ship, MCP config (owned)
issues/                  issues as people write them
.factory/                per task: the task, progress, runs and reports, proposals for owners
.github/                 workflows gate, autopilot, decide; CODEOWNERS
docs/                    design, eval, build log, thinking, use cases (the person's; agents leave it alone)
```

Run: `uv sync`, `uv run pytest`. Remote: private GitHub repo `Juicyscoop88/four-eyes`.

## Rules

- **Public or synthetic data only.** Nothing from FTMO, OANDA or any employer.
- **Keep it small.** A narrow thing that works and is honest about its limits.
- **Build log:** every working session adds an entry to [docs/build-log.md](docs/build-log.md): what was delegated, reviewed, written by hand, what went wrong, time spent. The brief requires it.
- **Mostly by directing agents.** Note in the build log what was written by hand.
- Everything in English. Never an em dash.
- Invariants and their property tests are changed only by a person.
