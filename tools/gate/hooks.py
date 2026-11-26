"""The plugin's hooks in Claude Code. They make the author's own session follow the rules early;
the gate in CI enforces the same rules for everyone, hooks or not.

- PreToolUse: an agent never edits an owned file and never writes something that looks like a secret.
- Stop: an agent that changed code is not done while an invariant is broken.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from gate.config import Factory
from gate.diff import changed_files, git
from gate.tests import run_suites

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

SECRETS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "GitLab token": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GCP service account key": re.compile(r'"private_key_id"\s*:\s*"[0-9a-f]{20,}"'),
}


def deny(reason: str) -> int:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


def handle(factory: Factory, event: str, raw: str) -> int:
    data = json.loads(raw or "{}")
    if event == "pre-tool-use":
        return pre_tool_use(factory, data)
    return stop(factory, data)


def pre_tool_use(factory: Factory, data: dict) -> int:
    if data.get("tool_name") not in WRITE_TOOLS:
        return 0
    tool_input = data.get("tool_input", {})
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    try:
        rel = Path(target).resolve().relative_to(factory.root.resolve()).as_posix()
    except ValueError:
        rel = target
    if factory.is_owned(rel):
        return deny(
            f"{rel} is owned by people (factory.yaml: owned). An agent never edits it. "
            "If an invariant looks wrong, stop and tell the person; they propose the change to its owners."
        )
    text = " ".join(str(tool_input.get(k, "")) for k in ("content", "new_string", "new_source"))
    text += " ".join(str(e.get("new_string", "")) for e in tool_input.get("edits", []))
    for name, pattern in SECRETS.items():
        if pattern.search(text):
            return deny(
                f"This looks like a {name}. Secrets never go into the repo: reference it from "
                "Secret Manager (or an environment variable) by name, never by value."
            )
    return 0


def stop(factory: Factory, data: dict) -> int:
    if data.get("stop_hook_active"):
        return 0  # one reminder per stop; the gate in CI is the guarantee
    try:
        base = git(factory.root, "merge-base", "HEAD", "main").strip()
    except subprocess.CalledProcessError:
        base = "HEAD"
    if not any(f.startswith("src/") for f in changed_files(factory.root, base)):
        return 0
    failures, _ = run_suites(factory, factory.root, only=("invariants",))
    if not failures:
        return 0
    lines = []
    for f in failures:
        m = re.match(r"(?:AssertionError: )?([A-Z]+-\d+):", f.message)
        inv = factory.invariant(m.group(1)) if m else None
        lines.append(f"- {inv.id}: {inv.statement} ({f.message})" if inv else f"- {f.test}: {f.message}")
    print(
        "You are not done: an owned invariant is broken by your change.\n" + "\n".join(lines) +
        "\nFix the code, not the invariant or its test.",
        file=sys.stderr,
    )
    return 2
