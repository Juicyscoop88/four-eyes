# Four Eyes: a software factory for FTMO & OANDA

> **People write issues. The factory does the rest, and nobody, human or agent, checks their own work.**

Finance already has the rule: a payment is not approved by the person who entered it (four eyes). The factory
applies it to code, whoever or whatever wrote it. Structured by the nine points of the brief, deep on three:
the protocol (3), quality and governance (6), adoption (8). Everything below runs in the prototype unless it
says *designed, not built*.

---

## 1. Definition

**A software factory is the contract every change must meet on its way to main, plus an autopilot that meets
it for you.** A person writes the issue (what and why) and makes the decisions only a person can make. The
factory does everything between: plan, tests, code, review, evidence. The wheel is always within reach: take
over at any step by hand, hand it back with "finish it".

On the brief's range it sits **automated by default, human at both ends**. It is not a new IDE, chat or
portal, not a deploy system (it ends at merge; their pipelines stay theirs), and not a mandate.

## 2. Problems and people, in order

| Order | Who | What the factory does |
|---|---|---|
| 1 | **Compliance lead** | Approver is never the author; every step is a commit by its role; secrets stopped before they exist |
| 1 | **Senior engineer** | Owned invariants enforced on every change; a review map of three decisions instead of 2,000 lines |
| 2 | **Early adopter** | Tests from a tester that never saw the code; measured, so rubber-stamping becomes visible |
| 3 | **Team lead** | One plugin for the team; honest numbers per change (cost, catches, time) |
| 3 | **Long tasks** | Progress file and one commit per step; any session or person continues from the branch |
| 4 | **Platform engineer** | Agents in their own workspaces with their own short-lived identity *(OIDC designed, key in the prototype)* |
| 5 | **Operations analyst** | The paved road *(designed, not built)* |

Compliance and the senior engineer come first: in a regulated trading firm they can block everything else,
and one mechanism (the gate) serves both. Left alone: how people write code, IDEs, deploy pipelines.

## 3. The design (deep)

### The path of one change, as the prototype ran it

The issue, as a person wrote it (UC8 from our use cases):

> *Last week the venue gateway redelivered execution reports after a reconnect and some fills were applied
> twice. Applying the same execution twice must not change the order a second time.*

| Step | Who | What happened (real run, 3.8 min, $0.81) |
|---|---|---|
| Plan | author agent | Wrote the task, the interface (`apply_execution`) and its assumptions |
| Blind tests | **tester**, another model | Wrote tests in a copy of the repo where every function body is `raise NotImplementedError` |
| Code | author agent | Implemented under the plugin's hooks until all suites were green |
| Gate | the gate | All suites; 6 faults injected into the changed lines: tester's tests caught 6, author's own 5 |
| Gaps | reviewer → tester | Faults nobody caught go to the reviewer, who rewrites them as behaviors in words; the tester adds tests, blind again. Loops until the tier's score is met |
| Invariants | tester → owners | The owned invariants caught 0 of 6: the tester proposed an extension; the gate measured it before an owner sees it |
| Review | **reviewer**, empty workspace | **Proposed a new owned invariant on its own: "an execution is applied at most once"** |
| Decide | **person** | Three decision cards in the pull request comment, each with answers to pick *(turning an answer into a change: being built)* |
| Merge | **another person** | CODEOWNERS for money paths; then their own pipeline |

### The protocol: isolation is physical

| Role | Sees | Never sees | Enforced by |
|---|---|---|---|
| Author | the repo | owned files as writable | PreToolUse hook denies the edit |
| Tester | task, invariants, signatures and docstrings | implementation, author's tests and chat | a workspace where they do not exist |
| Reviewer | task, diff, invariants, gate numbers | the author's conversation, the rest of the repo | an empty workspace |

A prompt that says "do not look at the code" is a wish. A workspace without the code is a guarantee. That is
also why the tester is **not** a Claude Code subagent: a subagent shares the author's workspace.

**Different models on purpose.** Same context isolation is not enough: the same model has the same blind
spots. The tester runs on a different model from the author (in the prototype Opus and Sonnet; at FTMO,
Gemini on the same Vertex AI account: another vendor, no new data processor).

### Three layers

1. **Advice** (skills, later an MCP with live facts per file): the agent does the right thing by itself.
2. **Guards** (hooks, local): it cannot edit an invariant, write a secret, or stop with an invariant broken.
3. **The rule** (the gate in CI): applies to everyone, plugin or not.

Efficiency comes from advice; safety comes from the rule.

## 4. People, day to day

- **Engineer:** writes an issue, answers decision cards. Or writes by hand as today and gets blind tests and
  a review map on the pull request for free.
- **Reviewer:** starts from the map. Approval means "I judged these three points": what the audit needs.
- **When it goes wrong:** a false block is overridden by the approver with a written reason. A bug that
  escapes becomes a new invariant (the reviewer proposed one unprompted in the run above).

## 5. Delegate, review, own

Agents draft everything: plan, tests, code, first review, invariant proposals. A person reviews the plan's
assumptions and the decision cards. A person **owns** what defines correctness (invariants) and what carries
accountability (approval). **Never handed to an agent:** editing invariants, approving a merge, production
credentials, rotating keys.

## 6. Quality, security, governance (deep)

### Measured, not "looks right": the eval

An adversary agent saw the finished code of three tasks and planted 15 realistic bugs. Each ran against
every suite ([eval.md](eval.md)):

| Check | Bugs caught |
|---|---|
| author's own tests | **5 of 15** |
| tester, blind, on Haiku / Sonnet / Opus | 13 / 15 / 14 of 15 |
| owned invariants | 0 of 15 |
| **the gate's tests** | **14 of 15** |
| reviewer, on the one no test caught | 1 of 1 |

What we learned, and changed:
- **The author's tests are the weak link**, exactly the early adopter's problem. They are measured, never counted.
- **A blind Haiku tester costs $0.01 to 0.02 and catches almost as much.** The expensive part of the factory
  does not have to be the checks.
- **Mutation scores saturate:** every tester scored 100%, so mutation does not tell a good tester from a weak
  one. It stays in the gate as a cheap floor; quality is measured by planted bugs.
- **Invariants catch catastrophes, not task details.** That is their job; tasks are covered by blind tests.

### Security

- **Secrets:** a hook blocks writing anything that looks like a key; gitleaks on every pull request; values
  only ever referenced by name. A leaked key is burned and rotated, encrypted or not.
- **Identity:** the report is posted by the CI bot, never an engineer's account. At FTMO: OIDC to Vertex AI,
  no long-lived key anywhere *(designed; the prototype uses a spend-limited key)*.

### Authorship, approval, audit

Every step is a commit by its role (`author agent`, `tester agent`, …) with `Requested-by`. The requester is
accountable for intent; a different person approves (CODEOWNERS on money paths). The report records which
roles ran, on which models, what they caught and what it cost.

### Risk tiers (`factory.yaml`)

`money` (orders, risk, payouts): invariants, mutation floor 80%, senior approver. `standard`: 50%. `low`: no floor.

## 7. Apps by non-engineers *(designed, not built)*

The analyst starts from a template app that already contains the way to production: the gate, hosting, data
only through a read-only masked API. Pushing deploys to an internal sandbox; production needs an engineer's
approval. The template is the process; engineering knows the app exists because the factory built it.

## 8. Adoption without a mandate (deep)

- **No install:** the plugin arrives with the repo (`.claude/settings.json`); one Enter. The gate is one CI
  include, or an org-wide policy set by the platform team.
- **Value before effort:** the first thing a skeptic sees is blind tests and a review map on *their own*
  hand-written pull request. They changed nothing and got something.
- **Never slower:** quiet when you are right. The first weeks it only reports.
- **The ladder, nobody has to climb:** 0 meet the gate in CI · 1 plugin locally · 2 answer decision cards ·
  3 write only issues. Everyone sees the next step.
- **The skeptical senior** keeps writing money code by hand; the factory tests and reviews it. Over weeks the
  numbers show where an agent would have been fine. Trust comes from their own data.

## 9. The first 90 days

| Weeks | Build | Learn |
|---|---|---|
| 1 to 2 | Gate, report only, on one FTMO and one OANDA repo | False alarm rate; what blind tests find on real code |
| 3 to 6 | Plugin, decision cards, invariants proposed for those repos | Review time; which tester model is worth it there |
| 7 to 10 | Gate blocks on `money`; OIDC; cost per change in Grafana | Cost per merged change; compliance's view of the trail |
| 11 to 13 | Autopilot from issues for volunteers; paved road design | Where people take the wheel, and why |

## Limits

- 15 planted bugs is a small sample, and the adversary is also Claude.
- The tester needs a clear interface; the author writes signatures first.
- Hooks cover Claude Code's file tools; a shell command is stopped only by the gate in CI.
- The reviewer misses things. It narrows attention; approval stays human.
- Invariants are only as good as their owners. The factory makes them cheap to propose, not correct.
