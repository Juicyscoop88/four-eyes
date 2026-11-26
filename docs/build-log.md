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
