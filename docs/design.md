# Four Eyes: a software factory for FTMO & OANDA

> **People write issues. The factory does the rest, and nobody, human or agent, checks their own work.**

**The bottleneck has moved from writing code to trusting it.** Agents already write more than people can
read: the senior engineer says reviewing takes longer than writing, the early adopter's pull requests are
approved unread, the team lead cannot tell whether anyone is faster. Faster writing makes all three worse.
The factory makes people productive by spending their attention only where a person is needed: a few
decisions per change, with evidence for everything else.

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
| 5 | **Operations analyst** | Setup adopts their tool: their promises become owned invariants, the same gate as engineers |

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
| Blind tests | **tester**, blind | Wrote tests in a copy of the repo where every function body is `raise NotImplementedError` |
| Code | author agent | Implemented under the plugin's hooks until all suites were green |
| Gate | the gate | All suites; 6 faults injected into the changed lines: tester's tests caught 6, author's own 5 |
| Gaps | reviewer → tester | Faults nobody caught go to the reviewer, who rewrites them as behaviors in words; the tester adds tests, blind again. Loops until the tier's score is met |
| Invariants | tester → owners | The owned invariants caught 0 of 6: the tester proposed an extension; the gate measured it before an owner sees it |
| Review | **reviewer**, empty workspace | **Proposed a new owned invariant on its own: "an execution is applied at most once"** |
| Decide | **person** | Three decision cards in the pull request comment, each with answers to pick (`/decide 2 reject`: the answer becomes a blind test first, then code) |
| Merge | **another person** | CODEOWNERS for money paths; then their own pipeline |

### After the merge: production stays the team's

Four Eyes ends at an approved merge, on purpose. Deploying is the team's existing pipeline, with its own
approvals, feature flags and rollback: a factory that agents drive should not hold production credentials in a
regulated firm, and nobody here would trust one that did. What crosses into production is the record: for any
line running there, `why` goes back to the commit, its role, the person who asked, the decisions on the cards,
the tests that fail when the line breaks and the approvals. A bug that escapes comes back as an issue and, when
it broke a promise, as a new owned invariant.

### The protocol: isolation is physical

| Role | Sees | Never sees | Enforced by |
|---|---|---|---|
| Author | the repo | owned files as writable | PreToolUse hook denies the edit |
| Tester | task, invariants, signatures and docstrings | implementation, author's tests and chat | a workspace where they do not exist |
| Reviewer | task, diff, invariants, gate numbers | the author's conversation, the rest of the repo | an empty workspace |

A prompt that says "do not look at the code" is a wish. A workspace without the code is a guarantee. That is
also why the tester is **not** a Claude Code subagent: a subagent shares the author's workspace.

**What it sees matters, not who it is.** We expected a different model to matter (different blind spots).
The eval says otherwise: a blind tester on the author's own model caught 15 of 15 planted bugs, the author's
tests 5. Isolation does the work, so the tester's model is a cost choice per repo (Haiku caught 13 for
$0.02), and another vendor (Gemini on the same Vertex AI account) stays an option, not a requirement.

**Hermetic.** Each role gets only the MCP servers `factory.yaml` names, and no settings of the laptop or
runner it runs on. Found on the bench: the author had loaded every server of the laptop (339 tools from 11
servers). Hermetic, the same bug cost five times less, and nothing could leave through a tool nobody approved.

### Three parts, each once

1. **The rule:** the gate in CI. Deterministic code: the verdict never waits on a model's judgment, and
   running it again gives the same answer. Any CI runs it; it is one command.
2. **The path:** issue → autopilot → pull request with decision cards → `/decide`. The same autopilot from
   an issue label in CI or from `/ship` on a laptop.
3. **The guide:** the plugin, with hooks (local guards) and the Four Eyes MCP for people and agents in
   Claude: `rules_for(path)` (owners, tier, invariants, standards) and `why(path, line)`.

**Code decides, agents advise.** Rules come in two kinds in `factory.yaml`: *invariants* (never broken,
property-tested, the gate blocks) and *standards* (how it is done here: a design system and optimistic UI
for apps, money handling for the core; served to the agent by `rules_for`, checked by the reviewer).
Standards come in two layers: *company* standards (basics, the design system, money) ship with the factory,
one version for every repo, and a repo only names them, so an update reaches all repos and none drifts;
*repo* standards are files for what only that repo does its own way, a choice made on purpose. MCP
tools differ per role: the author gets `rules_for`; the tester and reviewer get none, so nothing shows them
more than their role may see.

**General bug review is not rebuilt.** Anthropic's `code-review` plugin runs on every pull request through
the official `claude-code-action` (several agents, each finding validated before it is posted, inline comments),
and the same `/code-review` is enabled for every engineer locally. Four Eyes' reviewer does only what the factory
knows: the task, the owned invariants, the gate's numbers, the decision cards.

## 4. People, day to day

What each person gets is attention back, not speed:

| Who | Today | With Four Eyes |
|---|---|---|
| Senior engineer | reads 400 lines to trust them | answers the few cards only a person can decide (#479 on the bench: three questions) |
| Early adopter | ships fast, tests from the same agent | keeps the speed; tests come from someone who never saw the code |
| Team lead | setup lives in people's heads; no numbers | setup lives in the repo; time, cost and catches per change |
| Long tasks | the next session starts from scratch | the task, progress and every step are commits on the branch |
| Compliance | "who is the author?" | the person who asked plus the agent; an approver who is neither; `why` traces each decision |
| Analyst | a weekend tool nobody knows of | setup adopts it (secrets, client data, tests of what it promises), then `ship` or the issue form |

**Tried on a professional's repo, not only on ours.** On
[pandas_market_calendars](https://github.com/rsheftel/pandas_market_calendars) (exchange trading hours, 1700
tests, its own CI, CODEOWNERS and AGENTS.md, a test already red on main), alone, as four people:
- *the lead's setup* kept the team's CODEOWNERS, CI and AGENTS.md, turned four promises into owned invariants
  (each test checked by planting its bug) and found a real bug: two calendars not found by their own name;
- *the senior's fix by hand*: the gate caught a flaw in the senior's own test (green alone, red in the full
  suite), and its card asked the right question: which calendars does the guarantee cover?
- *a colleague's agent* handed in code it had never run; the most useful output was a card on a choice it made
  silently: do trading halts count as open minutes for the risk desk's limits?
- *the autopilot*: blind tests caught 84% of injected faults (27 of 32) and the bug I planted.

For the analyst the factory adds structure; for the senior it takes work away. The run also found six
problems in the factory, all fixed the same day: a test red on main blocked every pull request; each injected
fault ran the whole repo (the gate on one change: about 26 minutes, now 2, same score); a hand-made change got
no blind tests; setup could not correct its own draft and named a standard that did not fit; locking all of
`.github/` forbade the team's own rule for agents.

- **Where work starts:** an issue (the form asks what, why and an example). Or code by hand as today, which
  gets blind tests and a review map on the pull request for free.
- **Steering:** `/decide 2 reject`, `/decide A3 ...` in the pull request; or take the branch by hand and hand
  it back.
- **When it goes wrong:** a false block is overridden by the approver with a written reason. A bug that
  escapes becomes a new invariant (the reviewer proposed one unprompted in the run above).
- **How we know it works for them** (the pilot's numbers, not a promise): a person's minutes per merged
  change, defects that escape to production, the share of pull requests where the cards were enough, and the
  false alarm rate (a question asked that a person did not need).

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
- **So the factory tests its testers.** Once a week an adversary plants bugs in the open factory pull requests
  and measures what the blind tests catch (`calibrate` workflow). The number says how far a repo's tests can
  be trusted, and which tester model is worth its cost there.

### Security

- **Secrets:** a hook blocks writing anything that looks like a key; gitleaks on every pull request; values
  only ever referenced by name. A leaked key is burned and rotated, encrypted or not.
- **Identity:** the report is posted by the CI bot, never an engineer's account. At FTMO: OIDC to Vertex AI,
  no long-lived key anywhere *(designed; the prototype uses a spend-limited key)*.

### Authorship, approval, audit

Every step is a commit by its role (`author agent`, `tester agent`, …) with `Requested-by`. The requester is
accountable for intent; a different person approves (CODEOWNERS on money paths). The report records which
roles ran, on which models, what they caught and what it cost.

**`why` answers the regulator in one question.** Asked in Claude *"why does line 64 exist and who decided?"*,
the MCP returns the commit and its role, who asked, the person's decision on the card, the tests that fail
when that line is broken (found by breaking it), and the pull request with its approvals.

### Risk tiers (`factory.yaml`)

`money` (orders, risk, payouts): invariants, mutation floor 80%, senior approver. `standard`: 50%. `low`: no floor.

## 7. Apps by non-engineers

The analyst does not become an engineer. They say what their tool promises; the factory checks it as strictly
as engineers' code, and engineering learns the tool exists because it arrives as a pull request.

**Built: setup adopts a tool in any state.** `/four-eyes:setup` is the same skill for a lead's repo and an
analyst's folder. Run on a made-up weekend tool (a payout reconciliation script, a production export with
trader emails, a database password in the code, no git, no tests), it first showed a checklist in plain
Czech: the password ("rotate it, deleting it from the code does not fix copies already sent"), client data on
a laptop, no git and no tests, and a bug planted on purpose that it found on its own (a bank row missing from
the export was neither matched nor on the CHECK list, so a payout could vanish without a trace). Then it asked
what the analyst knows: where a mistake hurts clients or money, who approves, and what the tool must always
promise ("every row is either matched or flagged"). The promises became owned invariants with property tests
on a made-up sample, the exports left the repo, the password went to the secret manager. For a tool with a
page, it recommends the company design system and keeps the analyst's own look if they choose to.

**Designed, not built:** a template app that already contains the way to production (hosting, data only
through a read-only masked API, pushes to an internal sandbox, production after an engineer's approval).

## 8. Adoption without a mandate (deep)

- **No install:** the plugin arrives with the repo (`.claude/settings.json`); one Enter. The gate is one CI
  job, which a platform team can require across all repos.
- **Value before effort:** the first thing a skeptic sees is blind tests and a review map on *their own*
  hand-written pull request. They changed nothing and got something.
- **Never slower:** quiet when you are right. The first weeks it only reports.
- **The ladder, nobody has to climb:** 0 meet the gate in CI · 1 plugin locally · 2 answer decision cards ·
  3 write only issues. Everyone sees the next step.
- **The skeptical senior** keeps writing money code by hand; the factory tests and reviews it. Over weeks the
  numbers show where an agent would have been fine. Trust comes from their own data.

**Growth, not surveillance** *(designed, not built)*. Reviews hold what a person could learn: a junior on
the frontend keeps missing loading states, someone new to money code keeps missing boundaries. The factory
keeps that as a private profile **owned by the person**, built only from findings they confirmed: they see
it, `rules_for` reminds them at the right moment, and they share it with a mentor if they want. No ranking,
no score per person. A team lead sees only what the team misses as a whole, which becomes training, not a
verdict. A senior stops repeating the same review; a junior gets better faster.

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
- Checked on our sample domain, two open-source libraries and one professional repo, all Python. Blind tests
  and mutation work on Python only; another stack gets the guardrails, the reviewer and its own test suite.
- It stops at an approved merge: deployment is the team's pipeline (see "After the merge").
