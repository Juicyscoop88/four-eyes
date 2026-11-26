# Build log

The brief asks for: what was delegated, what was reviewed, what was written by hand, what went wrong, and how much time was spent.
Agent: Claude Code (Opus 5.5), directed from a team chat. Times are wall clock.

## 2026-11-26

**10:58 to 11:25: reading the brief (about 30 min)**
- The brief arrived as a PDF in Gmail; I shared a screen recording of scrolling through it. The agent read the frames, cropped and upscaled them, and transcribed the full text into `brief.md`.
- Reviewed: I read the brief myself in parallel.

**11:25 to 12:30: design conversation (about 1 h)**
- Delegated: research of the group's public job posts (tools, clouds, stacks), first proposals, use cases.
- Decided by me: do not change how engineers work; start from delivery; everyone uses Claude Code; GitLab, not GitHub; keep my own side project out of it.
- Went wrong: the first proposal (a chat-like interface) did not fit a company that already has Slack; dropped.

**11:40 to 11:50: sample domain (about 10 min, delegated)**
- Synthetic order handling, four owned invariants, property tests (Hypothesis).
- Verified: an injected overfill bug is caught ("ORD-1: filled 3 of 2"), then reverted.

**13:05 to 13:40: the MVP (about 35 min, delegated)**
- Delegated: the gate (`tools/gate`: suites, mutation testing, tester and reviewer runs, report), the plugin (hooks, `/ship`, role prompts), `.gitlab-ci.yml`, the demo branch.
- Decided by me: build only the core (tester in isolation, gate with invariants and mutation score, review map); shadow, provenance signing and the retro run stay in the design.
- Verified with real agents: the tester wrote 18 blind tests ($0.11); the seeded rushed change was blocked by 8 of them; the reviewer found a real gap nobody seeded (`Decimal("Infinity")` passed every check) and blocked; after the fix the gate passed, 9 of 9 faults caught by independent tests. In a real Claude Code session the plugin denied an edit of `invariants/orders.yaml`, and the Stop hook caught a deleted overfill check (ORD-1, ORD-4).
- Went wrong: the first idea, tester and reviewer as plugin subagents, would have let the tester read the code (a subagent shares the author's workspace). Moved to separate headless runs in their own workspaces.
- Not yet tried: the pipeline on gitlab.com.

**13:45 to 15:00: autopilot and the eval (about 1 h 15 min, delegated)**
- Decided by me: people write issues, the factory does the rest (autopilot by default, the wheel within reach); the tester on another model than the author (Gemini on Vertex later, not OpenAI: no new data processor for a regulated firm).
- Delegated: `gate autopilot` (plan, blind tests, code, gate, closing its own gaps through the reviewer, a proposal for the invariant owners, decision cards; every step a commit by its role; continues an existing branch when handed back), stronger mutation operators, `gate eval`.
- Ran: three issues of two to four sentences each (amend, duplicate fills, average price), all through to a passing gate unattended, 3.5 to 4 min and about $0.75 each. On the duplicate-fills incident the reviewer proposed a new owned invariant on its own ("an execution is applied at most once"), which is UC8.
- Eval: 15 bugs planted by an adversary agent. Author's own tests caught 5, the blind tester 13 to 15 depending on the model, the gate's tests 14, the reviewer the last one. Haiku as tester at $0.01 to 0.02 caught 13 of 15.
- Went wrong: the network dropped once mid-run (the run had to start over); mutation testing saturates (every tester scored 100%), so it does not tell good testers from weak ones, the planted bugs do; the owned invariants caught none of the planted bugs (they guard catastrophes, not task details).

**15:00 to 15:10: on GitHub (about 1 h with the design rewrite, delegated)**
- Decided by me: GitHub, not GitLab (the brief speaks of pull requests; GitLab came from one job post). A spend-limited key now, OIDC through a cloud (Bedrock here, Vertex at FTMO) as the design for no long-lived secret.
- Delegated: `docs/design.md` rewritten around "people write issues" (2,450 to 1,760 words, every claim backed by a run or the eval); workflows `gate` (every pull request, gitleaks, the report as a comment by the CI bot), `autopilot` (an issue labeled `autopilot` becomes a pull request), `decide` (`/decide 1 reject` by someone with write access becomes a blind test, then code); CODEOWNERS on the owned paths; `gate decide`.
- Ran: issue #2 (three sentences) became PR #3 in CI in 3.7 min for $0.55; `/decide 2 distinct` on PR #1 became a test and code in 2.6 min.
- Went wrong: the autopilot's author wrote its own entries into this build log (CLAUDE.md asks every session to); `docs/` is now the person's, the agent keeps `.factory/progress.md`. In CI there is no git user, so "who asked" failed until it came from the pull request. `/decide` first read the autopilot's cards, not the ones in the latest comment; the cards now travel in the comment. GitHub does not let Actions open pull requests by default (a repo setting); PR #3 was opened by hand.

**15:30 to 16:00: FourEyes MCP, then lighter (about 30 min, delegated)**
- Delegated: the FourEyes MCP in the plugin (`rules_for` with invariants and standards per path, `why` with the decisions and the tests that pin a line), checked in a real Claude Code session: asked in Czech why a line exists, Claude called `why` and named my `/decide` answer.
- Decided by me: keep it light. Nothing exists twice: the CLI only where there is no chat (CI, eval), the MCP for people and agents, one path (`/ship` starts the autopilot). Cut the CLI `why`/`rules`, the MCP `check`, `gate tests`, the seeded demo and the untested `.gitlab-ci.yml`. The name is FourEyes; the command is `foureyes` (was `gate`).

**16:00 to 17:00: issues for anyone, calibration, someone else's code (delegated)**
- Decided by me: help non-engineers write issues; the MCP is a registry of standards that grows without code; growth profiles owned by the person, never a ranking (designed only); test FourEyes on a foreign repo with real past bugs.
- Delegated: an issue form (what, why, example) that starts the autopilot on its own (issue #6 → PR #7, nobody touched it); the plan's assumptions as cards `A1..` changeable with `/decide`; FourEyes generalized to any Python repo (source folder, test command, interpreter in `factory.yaml`); the `calibrate` workflow (an adversary plants bugs in open factory pull requests weekly, ran in CI for $0.10); the bench on ten 2026 bugs of python-humanize.
- Went wrong: the plan wrote assumptions as `- A1.` instead of a numbered list, so PR #7 shows none (the parser now reads any list style, the plan is told the format). The proposal for invariant owners crashed on a repo without invariants. Calibration found 2 of 4 planted bugs nobody caught on the dust-fills task; the adversary itself called them near-equivalent edge cases, which is a limit of the method, said in the design.
