# Thinking notes (working draft, not for submission)

## What matters in the brief

- They grade the choice: "What you choose to go deep on is part of what we look at." 2 to 3 points deep, the rest one sentence.
- The seven people are the users. Design around them, not around agents.
- Prototype: runs live (plus recording), built mainly by directing agents, scaffolding readable (CLAUDE.md, prompts, configs, tests, evals), build log (delegated, reviewed, by hand, what went wrong, time), synthetic data only.
- Honesty: limits, trade-offs, what you would never hand to an agent. "A narrow thing that works and is honest about its limits beats a broad thing that doesn't."
- Time: about 4 hours suggested (the sprint page says up to 3). Spending more is fine if explained.
- Session: 35 to 40 min presentation and demo, the rest discussion. Due Tue 2026-12-01, presentation Thu 12-03 or Fri 12-04.

## What the job post tells us about their mental model

From careers.ftmo.com/job/ai-engineer (2026-11-22):
- Harness: initializer and coding-agent patterns, AGENTS.md/CLAUDE.md conventions, progress and checkpoint files, feature lists, end-to-end test loops for long sessions across many context windows.
- AI-native SDLC: each phase (plan, design, build, test, review, document, deploy) mapped to delegate / review / own. MCP integrations, eval loops, CI hooks.
- Infra: model access and routing, sandboxes, secrets and permissioning, observability, cost control for agent runs.
- Impact reporting: agreed metrics, adoption reported honestly, including where it fails.
- Citizen-built apps governed. Ambassador into teams, first win, leave them independent.

## What they already use (public postings, verify)

- AI tools: Claude Code, Antigravity (sprint page). Post also names Claude Agent SDK, Codex, Cursor.
- Cloud: Google Cloud (GKE, Cloud Run, Artifact Registry), Terraform, Helm, Kubernetes, Cloudflare.
- Source and CI: GitLab (FTMO cloud platform posting). OANDA unknown.
- Data/streaming: Kafka, Redis.
- Observability: Grafana, Prometheus, Loki, Mimir, Elastic, Splunk.
- Stacks: FTMO PHP, C++ (low latency), Python. OANDA Python FastAPI + React, Node 22 TypeScript (trading platform), older Java/Scala.

## Do not reinvent: what each need already has

| Need | Existing thing |
|---|---|
| Shared setup that does not leave with a person | CLAUDE.md / AGENTS.md, skills, hooks, plugin marketplace in a repo; Claude Code managed settings for org policy |
| Approver is not the author | GitLab MR approval rules (prevent approval by author), CODEOWNERS |
| Secrets, vulnerabilities | GitLab secret detection / SAST, gitleaks |
| Model access, routing, billing | Claude on Vertex AI (their GCP), or an LLM gateway |
| Observability and cost of agent runs | Claude Code OpenTelemetry export into their Grafana stack |
| Sandbox | Claude Code sandboxing, devcontainers, ephemeral GKE runners |
| Long tasks | progress file + feature list + init script (Anthropic's long-running harness pattern) |

The factory is mostly conventions and glue on top of these. What is genuinely missing is small: that is the part to build.

## Open questions to settle

1. Where on the range: tasks in, PRs out, or agent hand-off protocol?
2. Who first: senior trading engineer (correctness) or compliance (audit)? Probably both via the same mechanism.
3. What a human owns. Candidate: the invariants / acceptance spec, the risk tier, the approval, production.
4. Efficient vs responsible: review effort proportional to risk (risk tiers by path).
5. What makes a PR "perfect": small, one reason, tests from a separate agent written from the spec before the code, provenance, a review map that tells the human where to look.
6. Original angle: candidates below.

## Candidate original angles

- **Invariants are owned by humans, enforced by machines.** A file of invariants per domain (order handling) that agents can read but never edit (hook blocks it). Property tests generated from it gate every PR. Answers the senior engineer directly.
- **The review map.** Each PR states which lines need human judgment and why, everything else is proven by checks. Review time goes down, which is the senior's actual complaint.
- **Risk tiers.** Paths and change types decide the gate: docs and internal tools ship with one reviewer, order handling needs owned invariants plus a senior. Efficient where cheap, responsible where money moves.
