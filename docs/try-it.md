# Try it: Four Eyes by hand in Claude Code

Ten use cases, each a few prompts in a Claude Code terminal. About 30 minutes in all.
Each says what to type, what you should see, and what it shows.

Who does what:
- **The lead, once per repo:** `/four-eyes:setup` writes the guardrails (what is risky, who approves, what only
  people may change) into the repo as a pull request.
- **Every engineer, every day:** clones the repo and is asked once to install the plugin. Then one of two ways:
  - *hand it over:* `/four-eyes:ship <what and why>` turns the request into an issue and the factory builds it;
  - *work as today,* alone or with Claude: the plugin gives Claude each file's rules, and the gate checks the
    pull request however it was written.
- **Anyone without code (analyst):** the issue form on GitHub; the factory opens the pull request.

Two repos:
- **`~/Projects/ftmo-case-study`**: the factory's own repo, already on it (orders domain, invariants, standards).
- **`~/Projects/foureyes-try`**: a fresh clone of python-humanize, not on the factory yet. For installing.

Needs: `claude` signed in, `uv`, `gh` signed in (for the pull requests). The factory repo is public, nothing to sign in for.

---

## UC1. Set up a repo the factory has never seen (team lead, 5 min)

```bash
cd ~/Projects/foureyes-try && claude
```

1. `/plugin marketplace add Juicyscoop88/four-eyes`
2. `/plugin install four-eyes@four-eyes`, then restart Claude Code (`/exit`, `claude`).
3. `/four-eyes:setup`

**You should see:** Claude reads the repo and finds `src/humanize`, `tests`, the test command. It asks you one
question at a time (which paths carry money or trust, which files only people change). It writes on a branch
`four-eyes-setup`: `factory.yaml`, `.claude/settings.json` (Claude Code asks you first:
it protects `.claude/`), `.github/workflows/four-eyes.yml`, the issue form and `CODEOWNERS`. At the end it shows
the brief every session will get.

**Shows:** the plugin is standard Claude Code distribution (marketplace + `enabledPlugins` in the repo). Anyone who
clones this repo later is asked once to install it. Nothing is copied from our repo.

Check: `git log --stat -1` on the branch `four-eyes-setup`.

## UC1b. Bring an analyst's tool under the rules (operations analyst, 5 min)

`~/Projects/recon-tool-original` is a made-up reconciliation tool, "built with ChatGPT over a weekend": a script,
a morning report page in its own look, a production payouts export with trader emails, a database password in
the code, no git, no tests. Work on a fresh copy each time, the original stays as it is:

```bash
rm -rf ~/Projects/recon-try && cp -R ~/Projects/recon-tool-original ~/Projects/recon-try
cd ~/Projects/recon-try && claude
```

Say something in your own words, then `/four-eyes:setup`.

**You should see:** a checklist in plain words before anything changes: the password, the client data on a
laptop, no git, no tests, and a real bug (a bank row missing from the export is silently dropped: neither
matched nor on the CHECK list). Then questions about what you know: where a mistake hurts money, who approves,
and **what the tool must always promise** ("every row is either matched or flagged"). Those promises become
owned invariants with tests on a made-up sample; the exports leave the repo; the password goes to the secret
manager, with a note that it must be rotated.

**Shows:** the analyst does not become an engineer. They say what the tool promises; the factory checks it as
strictly as engineers' code, and engineering finally knows the tool exists.

## UC2. Guardrails while you write (engineer, 5 min)

```bash
cd ~/Projects/ftmo-case-study && claude
```

1. Look at the first lines Claude gets: ask `what do you know about this repo from the factory?`
   **You should see:** owned paths, risk tiers (money for `src/orders/**`), where invariants live.
2. `add a method to cancel the remaining quantity of an order in src/orders/engine.py`
   **You should see:** when Claude opens `engine.py`, it gets that file's rules without asking: tier money,
   invariants ORD-1 to 4, the money standard (Decimal, rounding). Its code follows them.
3. `change the invariant ORD-1 so it allows overfills`
   **You should see:** the edit of `invariants/orders.yaml` refused: owned by people. Claude tells you to propose
   it to the owners.
4. `put this API key in config: sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   **You should see:** refused, secrets never go into the repo.

**Shows:** the rules arrive by hooks, not by hoping the agent asks. The vibecoder gets them too.

Afterwards: `git checkout -- . && git clean -fd src tests` to drop the experiment.

## UC3. Ask the factory, not a colleague (engineer, 3 min)

Same session, three questions in plain words:
1. `why does line 18 of src/orders/engine.py exist?` → the MCP tool `why`: the issue, who asked, the decision, the tests that pin it.
2. `what is left on my branch before it can merge?` → `status`: changed files, their tiers, what the gate will ask for.
3. `from now on every amount we show is rounded half-even, make that a standard for src/**` → `propose_standard`:
   writes `standards/<name>.md` and shows the line an owner adds to `factory.yaml`. The agent never edits it itself.

**Shows:** the registry of standards grows from work, in a pull request, not from meetings.

## UC4. An idea to a pull request (`/ship`, any engineer or analyst, 6 min)

In `~/Projects/ftmo-case-study`:

`/four-eyes:ship orders should reject a limit price with more than 4 decimal places, a client sent 1.234567 and we stored it`

**You should see:** Claude writes `issues/<name>.md` in your words and waits for your go (this is where you steer).
Then the autopilot runs a few minutes on `factory/<name>`: plan, blind tests by a tester who never saw the code,
code, gate. It reports whether the gate passed, what the tests caught, and the decision cards ("A1: round or
reject?"). Answer one: `answer card 1: reject`. It becomes a blind test first, then code.

**Shows:** people write the issue, nobody checks their own work. Cost about $0.50 to 0.70.

## UC5. Your own pull request, the gate on GitHub (engineer who writes by hand, 5 min)

In `~/Projects/ftmo-case-study`, by hand or with Claude, outside the factory:
1. `git checkout -b try/own-pr`, change something small in `src/orders/engine.py`, commit, `gh pr create --fill`.
2. Wait for the `gate` check (about 3 min).

**You should see:** a comment by the CI bot: suites, injected faults caught per suite (your own tests measured,
not counted), and the review map with the lines that need a person. Separately, Anthropic's `code-review`
leaves inline comments on real bugs (none if it finds none). Locally the same: `/code-review` before you push. Then `/decide 1 <answer>` as a PR comment.

**Shows:** whoever writes it, the same gate. Local hooks can be bypassed, CI cannot.

Afterwards close the PR: `gh pr close --delete-branch`.

## UC6. Issue form, no code at all (analyst, 2 min + wait)

On GitHub, `Juicyscoop88/four-eyes` → Issues → New → **A change** form: what, why, an example. Submit.

**You should see:** the label `autopilot` starts the workflow; a pull request with blind tests and cards appears
in about 4 minutes. Nobody touched it.

## UC7. The company design system arrives by itself (analyst or engineer, 3 min)

In `~/Projects/recon-try` after UC1b, where you chose the company design system for the report:

`make the report page nicer, the ops team opens it every morning`

**You should see:** before Claude touches `report.py` it gets the company design system with its rules
(shared components, tokens, right-aligned numbers, money with its currency) and follows them; Comic Sans goes.
Ask `which rules apply to report.py?`: `rules_for` names the company standards and says that a reason to differ
goes to the design system's owners, not into this repo.

**Shows:** company standards live once, in the factory, and reach every repo in the same version. Nothing copied.

## UC8. The analyst changes their own tool (analyst, 6 min)

Same folder: `/four-eyes:ship the CHECK list should also say how big the difference is, so the team starts with the biggest`

**You should see:** the issue in your words, then the autopilot: blind tests written from your promises (every
row matched or flagged) by a tester that never saw the code, then the code, the gate, and cards in plain words
for what only you can decide ("absolute difference or percent?").

**Shows:** the analyst never writes a test, yet their tool is checked as strictly as engineers' code.

## UC9. The auditor asks who decided (compliance, 3 min)

In `~/Projects/ftmo-case-study`: `who asked for the rule that a fill can never exceed the order, who approved it, and which tests hold it?`

**You should see:** `why` traces the line to its issue, the person who asked, the decisions made on the cards
and the tests that pin it. On any factory pull request the gate comment ends with the provenance: who asked,
which agents checked it at what cost, which owned files were touched, and that the approver must be someone else.

**Shows:** "who is the author?" has an answer for every line, without asking anyone.

## UC10. The sceptical senior tries to break it (senior engineer, 5 min)

In `~/Projects/ftmo-case-study`:
1. `change ORD-1 in invariants/orders.yaml so overfills are allowed` → refused: the invariant is owned by people;
   Claude offers a proposal for its owners instead.
2. `make test_orders pass by loosening the assertion` → refused the same way: tests of invariants are owned too.
3. Change a guard in `src/orders/engine.py` by hand and run `/code-review`: the same bug review the gate runs in CI.

**Shows:** the rules hold whoever pushes, and the senior reviews three cards, not 400 lines.

---

## Not in the walkthrough

- **Telemetry** is described, not set up: Claude Code's built-in OpenTelemetry enabled company-wide through managed
  settings, plus one event per gate run (verdict, catches, cards, decisions, time from issue to merge), both to
  the company's Grafana. See `docs/design.md`.
- **The gate's blind tests and mutation** work on Python today. In another stack the guardrails and the reviewer
  work, the gate runs the project's own tests.

## From ftmo-factory (v0.3.3) to four-eyes (v0.3.4)

The plugin is now called `four-eyes`, its commands `/four-eyes:setup` and `/four-eyes:ship`. In Claude Code:
`claude plugin uninstall ftmo-factory@ftmo-factory`, `claude plugin marketplace remove ftmo-factory`, then
`claude plugin marketplace add Juicyscoop88/four-eyes` and `claude plugin install four-eyes@four-eyes`, and restart.
A repo set up before: in `.claude/settings.json` rename `ftmo-factory` to `four-eyes` (marketplace and plugin),
rename `.github/workflows/ftmo-factory.yml` and `.github/ISSUE_TEMPLATE/ftmo-factory.yml` to `four-eyes.yml`, and
move the workflow pins to `@v0.3.4`.

Since v0.3.3 the gate reports tests that already fail on the base branch instead of blocking on them (a failing
invariant still blocks), and each injected fault runs only the tests the gate counts, in parallel: on a repo with
1700 tests the gate went from about 26 minutes to 2. Since v0.3.4 a change written by hand gets blind tests at the
gate, and setup fits a mature repo (it keeps the team's agent rules possible and can correct its own draft).

## From v0.3.4 to v0.3.5

`/four-eyes:ship` shapes the issue with you before the factory starts: what, why, one example with numbers and
the expected outcome, and up to three open questions with the answer it would assume. Nothing to change in a
repo but the workflow pins (`@v0.3.5`).
