---
name: setup
description: Bring a repo or a folder under the Four Eyes software factory, whatever state it is in - an engineering repo, or a tool a non-engineer built with AI that runs on a laptop. Finds what is missing (repo, owner, secrets, production data, tests, what the tool promises), fixes what it can and shows exactly how to do the rest. Once per repo. Use when the person asks to set up, install, enable, adopt or add the factory, or to bring their tool under the company's rules.
---

You bring this repo or folder under the factory, once. The person may be a team lead setting up an
engineering repo, or a non-engineer (an analyst, an ops person) whose tool, built with AI, already runs and
that colleagues depend on. Never make them feel judged: the tool works, you make it safe to keep. Everything
goes into one branch and one pull request that the team reviews like any other change. The templates are at
the end of this file.

If the person is an engineer in a repo that is already set up (`factory.yaml` exists), call the MCP `status`,
say in two sentences that setup is done for this repo and that `/four-eyes:ship` or simply working with
Claude is what they want, and stop.

1. **Look before you ask.** Find out, without changing anything:
   - Is it a git repo, and does `origin` point to the company's GitHub? Who committed to it?
   - Language, package manager, source folder, tests and the command that runs them, any frontend and design
     system, `CLAUDE.md`, `AGENTS.md`, `.github/CODEOWNERS`, CI, linters. Read the README.
   - **The team's own rules for agents** (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`): they stay as they are.
     Note every place they tell an agent to write (plans in `.github/plans/`, a changelog in `docs/`): those
     paths must not become owned, or the factory forbids what the team asks for.
   - **Secrets in the code or in files** (`.env`, keys, passwords, connection strings).
   - **Production data in the folder** (exports: `.csv`, `.xlsx`, `.parquet`, database dumps) or code that
     reads such files or connects to production with a person's own credentials.
   - Where it runs today (a laptop, a cron on someone's machine) and who uses it, if the README says.
2. **Show what you found as a short checklist**, in plain words, each line ✅ or ⚠️ with one sentence why it
   matters. For example: "⚠️ The tool reads `export_2026-11.csv`, a production export, from this folder. A
   copy of client data on a laptop is the riskiest part; tests will run on a small made-up sample instead."
   Then say what you will fix in the branch and what the person must do themselves.
3. **Ask the person, one question at a time,** only what you could not find out:
   - where a mistake would hurt clients or money, and who approves those changes (the `money` tier);
   - what only people may change (configs, migrations, the rules below);
   - for a frontend: is it an internal FTMO app? Recommend the company design system ("Internal apps should
     look like one product, so colleagues do not learn a new screen. Use the company design system?"), with
     the answers *company design system (Recommended)* and *keep our own look*. If the repo already has its
     own design, never overwrite it: keeping it is a fine answer, made on purpose, and a reason to differ can
     go to the design system's owners later as a proposal;
   - **what the tool or code promises**: "What must always be true, whatever the input? For example: every
     row is either matched or flagged, totals on both sides are equal." Ask for two to five such promises in
     the person's words. They become owned invariants that the gate checks on every change.
   Ask each with the AskUserQuestion tool, one question per call, so the person clicks an answer. Ask about
   what the person knows (their product, their clients, their team), never about the factory's mechanics, and
   say in the same breath what the answer is for:
   - `question`: one or two plain sentences ending with "?", purpose first. For example: "Where would a mistake
     hurt clients or money? Changes there will always need a senior's approval, and their tests will be
     stricter." Never percentages, tiers or other factory terms in the question; never a bare word.
   - `header`: a short label of two or three words ("Client risk").
   - `options`: two to four. `label` in the person's words ("Payout calculations"), `description` the paths
     it means and what follows (the numbers, such as "tests must catch 80 % of planted bugs instead of 50 %",
     belong here, for whoever is curious). The recommended one goes first, its label ends with "(Recommended)".
   Write in the language the person uses with you in this conversation or in their CLAUDE.md; English if
   there is nothing to go by.
4. **Create the branch `four-eyes-setup` and fix what is missing there:**
   - Secrets: move them out of the code to environment variables read by name, add `.env` and the like to
     `.gitignore`, and tell the person which secrets to put into the company's secret manager. If a secret is
     already in git history, say so plainly: it must be rotated.
   - Production data: remove the exports from the repo and add them to `.gitignore`; write a small made-up
     sample with the same columns in `tests/data/` for the tests. If the tool must read production, it reads
     through a read-only connection named in config, never a file on a laptop; say who grants that access.
   - Promises: write them as `invariants/<name>.yaml` (template below), each with a property test in
     `tests/invariants/` that runs on the sample data. The approver reviews these tests in the pull request.
   - No git repo, or no company remote: `git init` here, and tell the person the exact command to create the
     repo on the company's GitHub (`gh repo create <org>/<name> --private --source . --push`); never create
     it yourself.
5. **Write, on the same branch,** in this order (`factory.yaml` last: once it is committed, the paths it
   names as owned are closed to agents; until the commit you may still correct it):
   - Standards: the company's ship with the factory and are only named in `factory.yaml` (`company: basics`,
     `company: design-system`, `company: money`), never copied, so every repo gets the same version and an
     update reaches all of them. Write a `standards/<name>.md` only for what this repo does its own way
     (its own look, if the person chose to keep it). Read a company standard before you name it, and name it
     only where its rules fit the code: `company: money` is for code that computes prices, amounts or
     balances, not for every path in the money tier (session times or configs carry risk but no amounts).
   - `.claude/settings.json`: merge in the template's `extraKnownMarketplaces` and `enabledPlugins`, keep
     everything already there. Everyone who clones the repo is then asked once to install the plugin, and Anthropic's
     `code-review` with it: `/code-review` before a push, the same review the gate runs in CI.
     Claude Code asks the person before it writes in `.claude/`; that is expected.
   - `.github/workflows/four-eyes.yml` from the template, `SETUP` replaced by the project's own setup command
     (for uv: `uv sync`; for pip: `pip install -e .[test]`).
   - `.github/ISSUE_TEMPLATE/four-eyes.yml` from the issue form template.
   - `.github/CODEOWNERS`: the money paths and the owned paths with the team the person named.
   - `factory.yaml` from the template, filled with what you found and heard. Delete the comments that do
     not apply. `python` is the interpreter the project's setup creates (for uv: `.venv/bin/python`); the
     test command runs with it (`.venv/bin/python -m pytest`).
   If a write is refused, tell the person which file and why. Never put drafts anywhere else.
6. **Check it loads:** run `foureyes hook session-start < /dev/null`. It prints the brief every session will
   get; show the person the paths and tiers it names. Fix `factory.yaml` until it is right, then commit.
7. **Commit and hand over, short.** Commit with a message that says what was set up. The checklist at the
   start was the long part; the hand-over is at most six lines, no tables, no file-by-file tour:
   - one line: what is done (for example "Set up on branch `four-eyes-setup`: rules, tests of your three
     promises, made-up sample data instead of the export.");
   - what is left for the person, numbered, one line each, at most three (for example: rotate the database
     password; open the pull request, or say "open it" and you do it with `gh`);
   - one line for the repo's admin if there is one: the repo secrets `ANTHROPIC_API_KEY` and, while the factory
     repo is private, `FOUREYES_TOKEN`, and the label `autopilot`;
   - one line: "Ask me about any file if you want the details."

The gate's blind tests and mutation testing work on Python today. In another stack say so plainly: the
guardrails while writing (the rules of each file, the standards) and the reviewer work; the gate runs the
project's own tests.

Never commit a secret, and never enable anything outside this repository.

## Templates

### factory.yaml

```yaml
# Four Eyes: the one file per repo. What people own, and how strict the gate is per path.
# Owned paths are changed only by their owners (CODEOWNERS approval). Agents never edit them.

owned:
  - factory.yaml
  - .github/workflows/**          # CI: the gate itself
  - .github/CODEOWNERS            # who approves
  # - invariants/**          # if this repo has invariants
  # - tests/invariants/**

source: src                       # the code the gate protects: stubbed for the tester, mutated by the gate
test_command: uv run pytest       # what the author agent runs
python: .venv/bin/python          # the interpreter that runs the suites (relative to the repo)

# invariants:                     # owned rules that must never break, each with its property test
#   - invariants/payments.yaml

# How things are done here. The agent gets them when it touches the paths, the reviewer checks them.
standards:
  - paths: ["**"]
    company: basics               # company standards ship with the factory: named here, never copied
  # - paths: ["apps/**", "web/**"]
  #   company: design-system      # internal apps look like one product
  # - paths: ["src/payments/**"]
  #   company: money
  # - paths: ["web/**"]
  #   file: standards/our-look.md # a repo standard: only what this repo does its own way

suites:
  author: tests                   # written by whoever wrote the code (measured, never counted)
  tester: tests/blind             # written by the tester, who never saw the code
  invariants: tests/invariants    # owned by people

tiers:
  money:                          # where a mistake costs money or trust
    paths: ["src/payments/**"]
    mutation_min: 0.8
    approver: senior              # CODEOWNERS team that approves
  standard:
    paths: ["src/**"]
    mutation_min: 0.5
  low:
    paths: ["**"]
    mutation_min: 0.0

agents:
  author:   { model: sonnet, mcp: [factory] }
  tester:   { model: sonnet, mcp: [] }   # isolation does the work; the model is a cost choice
  reviewer: { model: sonnet, mcp: [] }
```

### invariants/<name>.yaml (only when the person named promises)

```yaml
# What this tool promises, in its owner's words. Owned by people, never edited by an agent.
domain: reconciliation
paths: ["src/**"]          # the code these promises hold for
owners: ["@<the approver>"]
invariants:
  - id: REC-1
    statement: Every row is either matched or flagged, never dropped.
    why: A dropped row is a payment nobody looks at.
    test: tests/invariants/test_reconciliation.py::test_every_row_matched_or_flagged
```

Then in `factory.yaml`: `invariants: [invariants/<name>.yaml]`, `suites.invariants: tests/invariants`, and
`invariants/**` and `tests/invariants/**` under `owned`.

### .claude/settings.json (merge into the existing file)

```json
{
  "extraKnownMarketplaces": {
    "four-eyes": { "source": { "source": "github", "repo": "Juicyscoop88/four-eyes" } }
  },
  "enabledPlugins": { "four-eyes@four-eyes": true, "code-review@claude-plugins-official": true }
}
```

### .github/workflows/four-eyes.yml

```yaml
# Four Eyes on this repo: the gate on every pull request, the autopilot from an issue labeled `autopilot`,
# and `/decide` on a pull request. The workflows themselves live in the factory repo, pinned to a version.
name: four-eyes

on:
  pull_request:
  issues: { types: [labeled] }
  issue_comment: { types: [created] }

permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write   # Anthropic's code-review action in the gate

jobs:
  gate:
    if: github.event_name == 'pull_request'
    uses: Juicyscoop88/four-eyes/.github/workflows/gate.yml@v0.3.4
    with: { setup: "SETUP" }
    secrets: inherit   # ANTHROPIC_API_KEY for the reviewer; FOUREYES_TOKEN while the factory repo is private
  autopilot:
    if: github.event_name == 'issues'
    uses: Juicyscoop88/four-eyes/.github/workflows/autopilot.yml@v0.3.4
    with: { setup: "SETUP" }
    secrets: inherit
  decide:
    if: github.event_name == 'issue_comment'
    uses: Juicyscoop88/four-eyes/.github/workflows/decide.yml@v0.3.4
    with: { setup: "SETUP" }
    secrets: inherit
```

### .github/ISSUE_TEMPLATE/four-eyes.yml (the issue form)

```yaml
name: A change
description: Say what should change and why. The factory takes it from there and comes back with questions.
labels: [autopilot]
body:
  - type: textarea
    id: what
    attributes:
      label: What should change
      description: In your own words, as you would tell a colleague. No technical terms needed.
      placeholder: Traders want to change the size of a working order without canceling it.
    validations:
      required: true
  - type: textarea
    id: why
    attributes:
      label: Why
      description: Who needs it and what goes wrong today. This is what the factory checks the result against.
      placeholder: Canceling loses their place in the queue, and they do it ten times a day.
    validations:
      required: true
  - type: textarea
    id: example
    attributes:
      label: An example (optional)
      description: One concrete case with numbers, if you have one. It often becomes the first test.
      placeholder: An order for 10, 4 filled. Changed to 12, it should still need 8.
  - type: markdown
    attributes:
      value: |
        Where you leave something open, the factory makes an assumption and shows it on the pull request.
        You change any of them with one line, for example `/decide A3 reject it`.
```
