#!/usr/bin/env bash
# The demo, replayed from the demo/amend branch: one change from task to a gated merge request.
# Act 1 is the author's first try (seeded: a plausible rushed change whose own tests are green).
# Act 2 is the finished change, checked by the real reviewer agent.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
back=$(git rev-parse --abbrev-ref HEAD)
trap 'git checkout -q "$back"' EXIT
task=.factory/tasks/amend-quantity.md

step() { printf '\n\033[1m== %s\033[0m\n\n' "$1"; read -r -p "(enter) " _ </dev/tty || true; }

step "The task, as the person wrote it"
git checkout -q demo/1-rushed
cat "$task"

step "The author's first try. Its own tests are green"
git diff main -- src/orders/engine.py
uv run pytest tests/unit -q

step "The gate: the tester's blind tests catch what the author's tests missed"
uv run gate check --base main --task "$task" 2>/dev/null | sed -n '1,/### Tests/p' || true

step "The finished change: the gate with the reviewer, the merge request comment"
git checkout -q demo/amend
uv run gate check --base main --task "$task" --agents 2>/dev/null
