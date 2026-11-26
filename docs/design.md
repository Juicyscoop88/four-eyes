# Four Eyes: a software factory for FTMO & OANDA

*Draft design. Structured by the nine points of the brief. Deep on three: the four-eyes protocol (3), quality and governance (6), and adoption (8). The rest is kept short on purpose.*

---

## The idea

> We do not change how anyone writes code. We change what every change must prove before it merges, and nobody, human or agent, checks their own work.

Finance already has a rule for this: the four-eyes principle. A payment is not approved by the person who entered it. We apply the same rule to code, whoever or whatever wrote it.

---

## 1. Definition

**A software factory is the contract every change must meet on its way to main, plus the cheapest path to meeting it.**

- **Where it sits on the range:** in the middle, on purpose. A person decides at the start (what and why) and at the end (merge). Between them, everything is automated: tests, review, evidence. The author may be a person or an agent; the factory does not care.
- **What it is not:**
  - not a new IDE, chat or portal; engineers keep Claude Code, GitLab and Slack;
  - not a deploy system; it ends at merge, and their pipelines and environments stay theirs;
  - not a replacement for human approval on money-moving code;
  - not a mandate; nobody is told how to write code.

---

## 2. Problems and people, in order

| Order | Who | Problem | What the factory does |
|---|---|---|---|
| 1 | Security and compliance lead | No audit trail, author unclear, secrets and vulnerabilities | Provenance on every MR, approver is never the author, three secret locks |
| 1 | Senior engineer, trading | Agents quietly break invariants, review is slower than writing | Owned invariants enforced on every MR, review map, shadow agent |
| 2 | Early adopter | Huge PRs, self-written tests, rubber-stamp review | Tests from a separate tester, mutation score, small MRs |
| 3 | Platform engineer | Agents on laptops with personal credentials, no record, no cost view | Sandbox, own short-lived identity, cost per MR in Grafana |
| 3 | Team lead | Setups are personal and leave with people, no idea if faster | Conventions in one plugin, honest weekly numbers |
| 4 | Engineer with long tasks | Agents lose the thread across sessions | Harness: feature list, progress file, e2e loop |
| 5 | Operations analyst | Shadow IT on production exports | Paved road (designed, not built) |

**Why this order:** compliance and the senior engineer are first because in a regulated trading firm they can block everything else, and because one mechanism (the gate) serves both. Speed without their trust does not ship.

**Left alone for now:** how people write code, which models they prefer, IDE choice, deploy pipelines. Those work, or belong to other teams.

---

## 3. The design

### The whole system

```
   person or agent writes code          (unchanged: hand, Claude Code, anything)
              │
              ▼
   ┌───────────────────────────── the plugin (local, optional, faster) ─┐
   │  /ship:  author ──► tester ──► reviewer ──► merge request + map   │
   │  hooks:  never edit invariants · never write a secret · gitleaks   │
   └────────────────────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────── the gate (GitLab CI, mandatory) ──────┐
   │  same tester and reviewer, headless                                 │
   │  owned invariants · mutation score · SAST and secrets · risk tier   │
   │  writes: review map · provenance record                             │
   └────────────────────────────────────────────────────────────────────┘
              │
              ▼
   person approves (never the author) ──► merge ──► their own pipeline
```

Three things are ours. Everything else is what they have.

| Ours | Theirs, reused as is |
|---|---|
| The four-eyes protocol (tester and reviewer definitions, isolation) | Claude Code (plugins, subagents, hooks, managed settings, OpenTelemetry) |
| The gate job and its report | GitLab (MRs, approval rules, CODEOWNERS, secret detection, SAST, OIDC) |
| `factory.yaml` per repo: invariants and risk tiers | Claude on Vertex AI, GCP Workload Identity, Secret Manager, Grafana |

### One real change, from idea to production (UC2: trailing stop on OANDA's platform)

1. **Idea.** A product owner opens an issue: "trailing stop orders". *(person)*
2. **Plan.** The engineer runs `/ship` on the issue. The author agent writes a short plan and a feature list; the engineer edits it in two minutes. *(agent drafts, person steers)*
3. **Tests first, blind.** The tester agent gets the issue, the feature list, `factory.yaml` invariants and the public interface. It does **not** get the implementation, because it runs in a workspace where the implementation does not exist. It writes tests. *(agent)*
4. **Code.** The author agent implements until its own tests and the tester's tests pass. Hooks stop it from touching invariants or writing secrets. Progress goes to `progress.md`, so a new session continues where the last stopped. *(agent)*
5. **Review, blind.** The reviewer agent gets the diff, the issue and the invariants, not the author's conversation. It writes findings and a **review map**: the three places a person must judge, and why. *(agent)*
6. **Merge request.** Opened with the map and a provenance record. *(automatic)*
7. **Gate in CI.** Same tester and reviewer, headless, plus invariant property tests, mutation score, SAST and secret detection. The order-handling path is tier "money", so it requires a senior approver from CODEOWNERS. *(automatic)*
8. **Human review.** The senior reads the map, not 2,000 lines. Approves or sends back. *(person: owns the decision)*
9. **Merge and deploy.** Their existing pipeline takes over. *(theirs)*

### Zoom in: the four-eyes protocol, and why isolation is physical

The risky part of any multi-agent design is that the "independent" checker is not independent: same context, same assumptions, same blind spot. That is exactly the early adopter's problem (tests from the agent that wrote the code).

**Rule: isolation is enforced by what a role can see, not by what it is told.**

| Role | Sees | Never sees | How it is enforced |
|---|---|---|---|
| Author | everything in the repo | owned invariant files as writable | PreToolUse hook denies edits to paths in `factory.yaml: owned` |
| Tester | issue, feature list, invariants, public interface | implementation, author's reasoning | runs headless in a separate worktree where implementation files are removed |
| Reviewer | diff, issue, invariants | author's conversation | runs headless with a fresh context, gets only the diff and the issue |

A prompt that says "do not look at the code" is a wish. A workspace without the code is a guarantee. That is the line between a demo and something a compliance lead can sign.

**Why the tester's tests are worth more:** they encode what *should* happen, written before the code existed. The author's tests encode what the code *does*. The gate measures the difference with mutation testing: inject faults into the change, count which tests catch them. A typical result we want to show live: "author's tests caught 2 of 10, tester's tests 7 of 10, invariant tests caught the one that matters".

---

## 4. The people using it, day to day

- **Senior engineer.** Writes by hand as before. Sees the gate on his MRs (it is fast and quiet when he is right). Gets a review map on others' MRs: review gets shorter. Optional shadow agent shows, over weeks, where an agent would have been fine. Trust comes from his own data.
- **Early adopter.** Keeps the speed. `/ship` gives him the tester and reviewer locally, so CI rarely surprises him. His MRs get smaller because the harness splits work by feature.
- **Reviewer.** Starts from the map, not the diff. Approval means "I judged these three points", which is what the audit needs.
- **Team lead.** One plugin for the team. A weekly summary: what the gate caught, where agents passed, cost, and where AI lost.
- **Compliance.** Reads provenance records, does not chase people.
- **When it goes wrong:** a false alarm is overridden by the approver with a written reason (recorded). A missed bug in production becomes a new invariant (see 6). A broken gate fails open only for tier "low", never for "money".
- **How we know it works:** review time per MR, gate catches that a human confirmed, escaped defects per tier, adoption by ladder level, cost per merged MR. Reported honestly, including the losses.

---

## 5. Delegate, review, own

| | Delegate to agents | A person reviews | A person owns |
|---|---|---|---|
| Plan | feature list, draft plan | the plan (2 minutes) | what and why |
| Tests | tests from spec, property tests from invariants | new invariant proposals | the invariants |
| Code | implementation, refactors, migrations | the review map's points | architecture calls |
| Review | first review, mutation, SAST, secrets | findings the agent is unsure about | the approval |
| Release | release notes, changelog | | the decision to ship money-moving code |

**Why the line sits there:** a person owns what defines correctness (invariants) and what carries accountability (approval). An agent may propose both, never decide them. **Never handed to an agent:** editing invariants, approving a merge, touching production credentials, rotating keys.

---

## 6. Quality, security and governance

### Quality beyond "it looks right"
- **Owned invariants** per domain, each proven by a property test. An agent cannot change them; a change by a person needs an owner's approval (CODEOWNERS).
- **Mutation score** of the change: how many injected faults the tests catch. Reported per MR; a low score on tier "money" blocks.
- **Incidents become invariants.** Every postmortem ends with a new invariant and its test. The eval suite grows from real failures, not from invented ones.

### Security
- **Secrets, three locks:** the agent never sees values (only Secret Manager references); a hook blocks writing anything that looks like a key, gitleaks runs on commit; GitLab push protection and secret detection on push. If something still leaks, it is burned: the factory opens a rotation ticket with an owner and a deadline.
- **Where agents run:** a sandbox (Claude Code sandboxing locally, ephemeral runners in CI), with their own short-lived identity (GitLab OIDC to GCP Workload Identity), scoped to one repo. Never the engineer's credentials.
- **Vulnerabilities:** GitLab SAST and dependency scanning on every MR, plus the reviewer agent's security pass. New dependencies on tier "money" need a person.

### Authorship, approval, audit
- **Author** = the person who asked for the change (accountable for the intent).
- **Approver** = a different person (accountable for the decision). GitLab approval rules prevent the author approving.
- **Provenance record** on every MR: who asked, which agent and model, which roles ran, which checks passed with which results, cost, who approved. Signed as a GitLab attestation; queryable when the regulator asks.

### Risk tiers (`factory.yaml`)
| Tier | Example paths | Gate |
|---|---|---|
| money | order handling, risk rules, payouts | invariants, mutation threshold, senior approver |
| standard | product features | four eyes, one approver |
| low | docs, internal tools | four eyes, one approver, gate may fail open |

---

## 7. Apps built by non-engineers (designed, not built)

**The paved road.** The analyst starts from a template app that already contains the way to production: CI, the gate, hosting, and data access only through a read-only, masked API. He describes what he needs to an agent in plain words; pushing deploys to an internal sandbox; production needs an engineer's approval. He does not learn the process, the template is the process. Engineering knows the app exists because the factory built it.

We do not know their pipeline and hosting, so this is a design, not an implementation.

---

## 8. Adoption without a mandate

The plugin arrives with the repo: listed in `.claude/settings.json`, Claude Code offers it when the repo is opened. One keypress. Or the company enables it in managed settings.

**The first five minutes sell it:** `/factory` runs the gate over the engineer's last 20 merged MRs: "it would have flagged these 3, here is why". Value shown on his own past work, nothing to change.

**Day 1, invariants are not written from zero:** an agent proposes them from code, tests and bug history; the owner accepts or edits. Agent proposes, person owns.

**The ladder.** Nobody has to climb; everyone sees the next step.
0. Installs nothing. Meets the gate in CI.
1. Plugin locally. Same checks, minutes earlier.
2. `/ship`. The agent is the author.
3. Long tasks through the harness.
4. The module is trusted. The shadow switches off.

**The senior who does not see the point** never has to change. The shadow agent works on a sample of his tickets on risky paths, with a cheaper model, and stops once the module has a track record. After a month he has data, not opinions.

**The early adopter's habits** come up to standard without a talk: the gate scores his tests, the harness keeps his MRs small.

---

## 9. The first 90 days

| Weeks | Build | Expect to learn |
|---|---|---|
| 1 to 2 | Gate in CI (no install) on one FTMO and one OANDA repo, tier "money" only, report only, nothing blocks | False alarm rate, what the retro run finds on past MRs |
| 3 to 6 | Plugin with tester, reviewer, hooks, `/ship`; invariants proposed for those repos | Whether blind tests beat author tests in practice; review time |
| 7 to 10 | Gate starts blocking on tier "money"; provenance records; cost per MR in Grafana | Cost per merged MR, compliance's view of the records |
| 11 to 13 | Shadow agent on a sample; harness for long tasks; paved road design with platform | Where agents are trusted per module; what the analyst lane needs |

Adoption is reported honestly every two weeks, including where it fails.

---

## Limits and trade-offs

- **Invariants are only as good as the people who own them.** The factory makes them cheap to propose and enforce, not correct.
- **Mutation testing costs CI time.** Run on changed code only, full only on tier "money".
- **Blind tests need a clear interface.** Where a change has no stable interface yet, the tester works from the spec only and catches less.
- **The reviewer agent misses things.** It narrows human attention; it does not replace it. That is why approval stays human.
- **Shadow agents cost tokens.** Sampled, cheaper model, and switched off per module.
- **What we did not design:** deploy pipelines, hosting, IDE choice, model selection policy.
