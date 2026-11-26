# Use cases: how FTMO & OANDA probably work, and what the factory changes

Assumptions from public information only (job posts, product pages). To verify on the recruiter call.
FTMO: prop firm. Traders buy an evaluation (Challenge, Verification), trade on platforms such as MT4/MT5, cTrader, DXtrade; risk rules (max daily loss, max loss, profit target) decide pass or fail; funded traders get payouts. Stacks: PHP, Python, C++ (low latency), GitLab, GCP.
OANDA: regulated broker in several jurisdictions. Order execution, client money, KYC, regulatory reporting. Stacks: Python FastAPI + React, Node 22 TypeScript on GKE with Kafka and Redis.

Parts of the factory referenced below:
- **Harness**: agent in a sandbox with its own identity, feature list, progress file, init script, e2e loop; conventions from a shared plugin.
- **Gate**: at every merge request, whoever wrote it: owned invariants, independent AI review, mutation score, secrets/SAST, risk tier, review map, provenance.
- **Shadow**: an agent solves the same ticket in parallel; the gate compares.
- **Lanes**: engineer lane and analyst lane (template, read-only data, stricter limits).

---

## UC1. A risk rule changes (FTMO, senior engineer)
Product wants max daily loss to count floating P&L at a new cut-off time.
- **Today:** the senior writes it by hand, because an agent once broke an invariant in this code. Slow but trusted.
- **With the factory:** nothing changes for him. He writes it by hand. A shadow agent writes its own version. The gate runs both against the owned invariants (a breach is never missed, daily loss resets once per day). His MR gets a review map; the shadow's result goes to a weekly report.
- **What he gets:** after a month, data on where the agent would have been fine. Trust from evidence, not from a mandate.

## UC2. A new order type (OANDA trading platform, early adopter)
Trailing stop on the Node/TypeScript platform.
- **Today:** one 2,000-line agent PR, tests by the same agent, approved after a skim.
- **With the factory:** the harness splits it into a feature list and small MRs. Tests come from a separate agent, written from the spec and the invariants before the code. The gate shows mutation score: the agent's own tests caught 2 of 10 injected bugs, the invariant tests 10 of 10. The reviewer's map points at the 3 lines that need judgment.
- **What changes:** speed stays, rubber-stamping goes, because the PR proves what the reviewer used to assume.

## UC3. Two companies, one way of working (team lead)
After the acquisition, FTMO and OANDA teams use different tools and prompts.
- **Today:** every setup is personal and leaves with the person. Nobody knows if AI helps.
- **With the factory:** conventions ship as one internal Claude Code plugin (CLAUDE.md templates, skills, hooks), installed with one command, versioned like code. Agent telemetry (OpenTelemetry) goes to the Grafana they have. Shadow and gate data answer "are we faster?" per team, honestly, including where AI loses.

## UC4. A migration that takes days (engineer with long tasks)
Move the payout calculation from a legacy PHP service to Python.
- **Today:** the agent loses the thread after a context window; the next session starts from scratch.
- **With the factory:** an initializer agent writes the feature list, the init script and the e2e check. Each coding session takes one feature, leaves the progress file and a commit, and the next one starts by reading them. Old and new service run on the same synthetic payouts; the e2e loop compares outputs.

## UC5. Agents with production credentials (platform engineer)
- **Today:** agents run on laptops with the engineer's own access. No record, no cost view.
- **With the factory:** agents run in a sandbox (Claude Code sandboxing locally, ephemeral GKE runners in CI) with their own short-lived identity (GitLab OIDC to GCP Workload Identity), scoped to the repo. Models through Vertex AI. Every run reports tokens and cost per MR to Grafana. Secrets never reach the agent's context.

## UC6. The regulator asks (security and compliance lead)
"Who changed the payout calculation on 12 March, who approved it, and how do you know it is correct?"
- **Today:** dig through Slack, Git history and memory.
- **With the factory:** every MR carries a signed record: who asked for it, which agent and model, what it touched, which invariants and checks passed, who approved (never the author, enforced by GitLab approval rules). The answer is one query. Author = the person who asked; accountable = the approver.

## UC7. The weekend reconciliation tool (operations analyst)
Payouts vs bank statements, built with an AI assistant, running on a laptop against a production export.
- **Today:** shadow IT. Five people depend on it, engineering does not know.
- **With the factory:** the analyst lane. Start from a template app, describe the need in plain words, the agent builds it. Data only through a read-only, masked replica API. The same gate runs, with an engineer as the approver for anything touching money. The app is registered, hosted, owned. Engineering knows it exists because the factory built it.

## UC8. A bug reaches production (everyone)
A partial fill is reported twice after a Kafka redelivery.
- **Today:** fix, postmortem, a Confluence page nobody reads.
- **With the factory:** the postmortem ends with a new owned invariant ("a fill id is applied at most once") and its property test. From then on, every MR, human or agent, is checked against it. The factory learns from real failures, and the eval suite grows from them.
