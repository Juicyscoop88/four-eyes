---
name: init
description: Put this repository on the FourEyes factory - factory.yaml, standards, the plugin for everyone who clones it, the gate in CI and the issue form. Use when the person asks to set up, install, enable or add FourEyes to a repo.
---

You set FourEyes up in this repository for the person. Everything goes into one branch and one pull request
that the team reviews like any other change. The templates are at the end of this file.

1. **Already on it?** If `factory.yaml` exists, say so, call the FourEyes MCP `status` and stop.
2. **Look before you ask.** Find the language and package manager (`pyproject.toml`, `package.json`, ...), the
   source folder, the test folder and the command that runs the tests, any frontend (apps, web, ui), a design
   system or style guide, `CLAUDE.md`, `.github/CODEOWNERS` and the CI it uses. Read the README.
3. **Ask the person, one question at a time,** each with two or three answers to pick, only what you could not
   find out:
   - which paths carry money or trust (they become the `money` tier) and which team approves them;
   - which files only people may change (configs, migrations, invariants);
   - for a frontend, where the design system is.

   Ask each with the AskUserQuestion tool, one question per call, so the person clicks an answer. The person
   may not know FourEyes, so each question reads on its own, like a good form:
   - `question`: a real question in full sentences: one sentence of context in plain words, then the question
     itself, ending with "?". No FourEyes terms. For example: "A mistake in some files costs more than in
     others. FourEyes checks those files more strictly: the tests must catch 80 % of planted bugs instead of
     50 %, and a named team approves every change. Which files in this repo should get the stricter check?"
   - `header`: a short label of two or three words ("Risky files").
   - `options`: two to four. `label` a few words, `description` what follows from picking it. The recommended
     one goes first and its label ends with "(Recommended)".
   Write in the language the person uses with you in this conversation or in their CLAUDE.md; English if
   there is nothing to go by. Never put a question only into the answers, and never a bare word as the question.
4. **Write, on a branch `foureyes-init`,** in this order (`factory.yaml` last: once it exists, the paths it
   names as owned are closed to agents, including `.github/`):
   - `standards/basics.md` from the template. For a frontend, also `standards/design-system.md`: the design
     system's rules in a few bullets, with a link to where it lives.
   - `.claude/settings.json`: merge in the template's `extraKnownMarketplaces` and `enabledPlugins`, keep
     everything already there. Everyone who clones the repo is then asked once to install the plugin, and Anthropic's
     `code-review` with it: `/code-review` before a push, the same review the gate runs in CI.
     Claude Code asks the person before it writes in `.claude/`; that is expected.
   - `.github/workflows/foureyes.yml` from the template, `SETUP` replaced by the project's own setup command
     (for uv: `uv sync`; for pip: `pip install -e .[test]`).
   - `.github/ISSUE_TEMPLATE/foureyes.yml` from the issue form template.
   - `.github/CODEOWNERS`: the money paths and the owned paths with the team the person named.
   - `factory.yaml` from the template, filled with what you found and heard. Delete the comments that do
     not apply. `python` is the interpreter the project's setup creates (for uv: `.venv/bin/python`); the
     test command runs with it (`.venv/bin/python -m pytest`). A design system goes under `standards:`.
   If a write is refused, tell the person which file and why. Never put drafts anywhere else.
5. **Check it loads:** run `foureyes hook session-start < /dev/null`. It prints the brief every session will
   get; show the person the paths and tiers it names. Fix `factory.yaml` until it is right.
6. **Commit and hand over.** Commit with a message that says what was set up. Tell the person in a few lines
   what each file does and what is left for them:
   - open the pull request (or ask you to, with `gh`);
   - add the repo secrets `ANTHROPIC_API_KEY` (the reviewer and autopilot in CI) and, while the FourEyes repo
     is private, `FOUREYES_TOKEN` (a read-only token for it);
   - create the label `autopilot`.

The gate's blind tests and mutation testing work on Python today. In another stack say so plainly: the
guardrails while writing (the rules of each file, the standards) and the reviewer work; the gate runs the
project's own tests.

Never commit a secret, and never enable anything outside this repository.

## Templates

### factory.yaml

```yaml
# FourEyes: the one file per repo. What people own, and how strict the gate is per path.
# Owned paths are changed only by their owners (CODEOWNERS approval). Agents never edit them.

owned:
  - factory.yaml
  - .github/**
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
    file: standards/basics.md
  # - paths: ["apps/**", "web/**"]
  #   file: standards/design-system.md

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
  author:   { model: sonnet, mcp: [foureyes] }
  tester:   { model: sonnet, mcp: [] }   # isolation does the work; the model is a cost choice
  reviewer: { model: sonnet, mcp: [] }
```

### standards/basics.md

```markdown
# Basics

How every change is made here, whoever writes it.

- A change does one thing. Say in the pull request what and why, in a sentence a colleague understands.
- Behavior comes with a test that fails without the change. Tests name the case they check.
- Errors are handled where they happen, with a message a person can act on. Nothing is swallowed silently.
- No secrets in code, config or tests: reference them by name from the secret store or the environment.
- No new dependency without a reason in the pull request. Prefer what the repo already uses.
- Inputs from outside (users, files, APIs) are validated before they are used.
- Names say what things are. No dead code, no commented-out code, no TODO without an issue.
```

### .claude/settings.json (merge into the existing file)

```json
{
  "extraKnownMarketplaces": {
    "foureyes": { "source": { "source": "github", "repo": "Juicyscoop88/four-eyes" } }
  },
  "enabledPlugins": { "four-eyes@foureyes": true, "code-review@claude-plugins-official": true }
}
```

### .github/workflows/foureyes.yml

```yaml
# FourEyes on this repo: the gate on every pull request, the autopilot from an issue labeled `autopilot`,
# and `/decide` on a pull request. The workflows themselves live in the FourEyes repo, pinned to a version.
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
    uses: Juicyscoop88/four-eyes/.github/workflows/gate.yml@v0.2.2
    with: { setup: "SETUP" }
    secrets: inherit   # ANTHROPIC_API_KEY for the reviewer; FOUREYES_TOKEN while the FourEyes repo is private
  autopilot:
    if: github.event_name == 'issues'
    uses: Juicyscoop88/four-eyes/.github/workflows/autopilot.yml@v0.2.2
    with: { setup: "SETUP" }
    secrets: inherit
  decide:
    if: github.event_name == 'issue_comment'
    uses: Juicyscoop88/four-eyes/.github/workflows/decide.yml@v0.2.2
    with: { setup: "SETUP" }
    secrets: inherit
```

### .github/ISSUE_TEMPLATE/foureyes.yml (the issue form)

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
