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

**2026-11-27 09:00 to 10:00: hermetic agents, the bench finished (delegated)**
- Decided by me: the factory's agents are hermetic, in general, not as a cost fix: each role gets only the MCP servers `factory.yaml` names, no user settings of the machine it runs on.
- Delegated: per-role `mcp:` in `factory.yaml` (`--strict-mcp-config`, `--setting-sources project`); the plan must write its task, with one clear ask back; bench reruns merge their rows and start from a fresh branch.
- Ran: #334, #346, #392 and #479 again. 9 of 10 bugs fixed from the issue alone, the maintainers' hidden tests pass on every one the gate passed. #479 was blocked with three questions for a person, and the hidden tests confirm it was not right yet. Cost per bug fell from about $3 to $0.52 to $0.62.
- Went wrong: the first rerun continued the last run's branches (the gate re-ran old code), caught by reading the logs, stopped and restarted.

**2026-11-27 10:00 to 12:45: install anywhere, setup for leads and analysts (delegated, tested by me in Claude Code)**
- Decided by me: the factory installs like any Claude Code plugin from a marketplace and arrives with the repo; bug review is Anthropic's `code-review`, not ours (ours keeps the task, the invariants and the cards); the name people see is the company's (`ftmo-factory`, `/ftmo-factory:setup`, `/ftmo-factory:ship`), four eyes stays the principle; setup asks about purpose, not mechanics; one setup for a lead's repo and an analyst's weekend tool; company standards live once, in the factory.
- Delegated: the plugin carries the engine pinned to a release (hooks 2 s to 0.1 s per call), rules arrive with the first read of a file, reusable workflows, MCP `status` and `propose_standard`; setup that finds what is missing (git, owner, secrets, production data, tests, what the tool promises), fixes it on a branch and ends in a few lines; company standards (basics, design system, money) in the factory, named per repo; ten use cases in `docs/try-it.md`. Releases v0.2.1 to v0.3.2.
- Ran: setup on a made-up weekend tool (password in the code, an export with trader emails, no git, a bug planted on purpose): it found the bug on its own, turned "every row is matched or flagged" into owned invariants with tests on a made-up sample, removed the exports and the password, recommended the company design system for the report page and named it without copying.
- Went wrong: my own test of setup on a uv repo showed the gate reporting a broken invariant on correct code (the venv's python was resolved to the system one, without pytest); Claude refused to work around it, the fix was one line and a test (v0.3.1). The rename first reached only the plugin, not the MCP server and texts people see. The gate on the factory's own pull requests asked good questions each time (version pins, migration of repos on the old names, whether company standards should be pinned); I answered them and they became a migration note.

**2026-11-27 12:20 to 15:00: the factory on a professional repo (delegated and run unattended, decisions by me)**
- Decided by me: test what the factory does for a professional, not only for a vibe coder; the agent finds a mature repo and runs it alone. Six decision cards on the factory's own pull requests (a broken invariant blocks even when it was red before; only the independent suites and the change's own tests run per fault; an owned file locks once committed, and an error never unlocks it). The public name is Four Eyes, not FTMO's: the four-eyes principle is the compliance term for exactly this, and the repo must not look like an FTMO product.
- Delegated: setup, a hand-made fix, a colleague's agent and the autopilot on `pandas_market_calendars` (1700 tests, its own CI, CODEOWNERS and AGENTS.md, a test red on main); the fixes and their tests (v0.3.3, v0.3.4).
- Ran: setup kept the team's CODEOWNERS, CI and AGENTS.md, wrote the lead's four promises as invariants and checked each by planting its bug; it found a real bug (two calendars not found by their own name) and the red test. The gate caught a flaw in the senior's own test (green alone, red in the full suite). A colleague's agent handed in code it had never run (2 of 8 of its tests red); the most useful output was a card on a choice it made silently (do trading halts count as open minutes?). The autopilot's blind tests caught 84% of injected faults and the bug I planted.
- Went wrong: the test red on main blocked every pull request and sent the autopilot's author to fix it; each of 32 faults ran the whole repo, 25 minutes; the autopilot repeated mutation when nothing was left to test (stopped by hand at 38 minutes); a hand-made change got no blind tests although design.md said so; setup named the money standard for session times and then could not correct factory.yaml; locking all of `.github/` forbade the team's own AGENTS.md rule (plans in `.github/plans/`). All fixed; the gate on the same change now takes 2 minutes with the same score. I also tried to answer the gate's cards on my own pull request; Claude Code refused, as it should: nobody approves their own work.
