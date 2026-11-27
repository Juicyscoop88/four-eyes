# Basics

How every change is made here, whoever writes it.

- A change does one thing. Say in the pull request what and why, in a sentence a colleague understands.
- Behavior comes with a test that fails without the change. Tests name the case they check.
- Errors are handled where they happen, with a message a person can act on. Nothing is swallowed silently.
- No secrets in code, config or tests: reference them by name from the secret store or the environment.
- No new dependency without a reason in the pull request. Prefer what the repo already uses.
- Inputs from outside (users, files, APIs) are validated before they are used.
- Names say what things are. No dead code, no commented-out code, no TODO without an issue.
