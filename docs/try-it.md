# Try it: FourEyes by hand in Claude Code

Six use cases, each a few prompts in a Claude Code terminal. About 30 minutes in all.
Each says what to type, what you should see, and what it shows.

Two repos:
- **`~/Projects/ftmo-case-study`**: FourEyes' own repo, already on the factory (orders domain, invariants, standards).
- **`~/Projects/foureyes-try`**: a fresh clone of python-humanize, not on the factory yet. For installing.

Needs: `claude` signed in, `uv`, `gh` signed in (the FourEyes repo is private, git reads it with your login).

---

## UC1. Install FourEyes in a repo it has never seen (team lead, 5 min)

```bash
cd ~/Projects/foureyes-try && claude
```

1. `/plugin marketplace add Juicyscoop88/four-eyes`
2. `/plugin install four-eyes@foureyes`, then restart Claude Code (`/exit`, `claude`).
3. `/four-eyes:init`

**You should see:** Claude reads the repo and finds `src/humanize`, `tests`, the test command. It asks you one
question at a time (which paths carry money or trust, which files only people change). It writes on a branch
`foureyes-init`: `factory.yaml`, `standards/basics.md`, `.claude/settings.json` (Claude Code asks you first:
it protects `.claude/`), `.github/workflows/foureyes.yml`, the issue form and `CODEOWNERS`. At the end it shows
the brief every session will get.

**Shows:** the plugin is standard Claude Code distribution (marketplace + `enabledPlugins` in the repo). Anyone who
clones this repo later is asked once to install it. Nothing is copied from our repo.

Check: `git log --stat -1` on the branch `foureyes-init`.

## UC2. Guardrails while you write (engineer, 5 min)

```bash
cd ~/Projects/ftmo-case-study && claude
```

1. Look at the first lines Claude gets: ask `what do you know about this repo from FourEyes?`
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

## UC3. Ask FourEyes, not a colleague (engineer, 3 min)

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

---

## Not in the walkthrough

- **Telemetry** is described, not set up: Claude Code's built-in OpenTelemetry enabled company-wide through managed
  settings, plus one event per gate run (verdict, catches, cards, decisions, time from issue to merge), both to
  the company's Grafana. See `docs/design.md`.
- **The gate's blind tests and mutation** work on Python today. In another stack the guardrails and the reviewer
  work, the gate runs the project's own tests.
