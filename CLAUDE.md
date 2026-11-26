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

## Delivery (start here)

The factory is a **Claude Code plugin** that arrives with the repo: listed in the repo's `.claude/settings.json`, so opening the repo in Claude Code offers to install it (or the company enables it in managed settings). No download, no manual.

The plugin holds:
- subagent `tester`, subagent `reviewer` (the four eyes);
- hooks: an agent never edits invariants; invariant tests run before an agent says it is done;
- skill `/ship`: author, then tester, then reviewer, then a merge request with a review map;
- later: an MCP server for live knowledge (how to use the factory, gate results, track record of a module).

The **same** tester and reviewer run headless (`claude -p`) in GitLab CI on every merge request. Locally it is faster feedback; in CI it is the rule. Whoever skips `/ship` meets the same gate later.

## Parts on top of the core (decided, not yet built)

- **Shadow agent** for skeptical seniors: solves the same ticket in parallel, the gate compares. Only risky paths, a sample of tickets, a cheaper model; switches itself off per module once the agent has a track record.
- **Mutation score:** the gate injects bugs and measures how many the tests catch. Quality beyond "it looks right".
- **Review map:** the merge request says which few lines need human judgment and why.
- **Provenance:** who asked, which agent and model, what it touched, which checks passed, who approved (never the author).
- **Incidents become invariants:** a postmortem ends with a new owned invariant and its test.

## This repo

```
brief.md                 the assignment, transcribed
invariants/orders.yaml   owned invariants of the sample domain
src/orders/              synthetic order handling: the code the factory protects
src/gate/                the gate (in progress)
tests/invariants/        property tests that prove the invariants (owned like them)
tests/unit/              ordinary tests
docs/                    thinking, use cases, build log
```

Run: `uv sync`, `uv run pytest`.

## Rules

- **Public or synthetic data only.** Nothing from FTMO, OANDA or any employer.
- **Keep it small.** A narrow thing that works and is honest about its limits.
- **Build log:** every working session adds an entry to [docs/build-log.md](docs/build-log.md): what was delegated, reviewed, written by hand, what went wrong, time spent. The brief requires it.
- **Mostly by directing agents.** Note in the build log what was written by hand.
- Everything in English. Never an em dash.
- Invariants and their property tests are changed only by a person.
