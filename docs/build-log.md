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
