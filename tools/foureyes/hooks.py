"""The plugin's hooks in Claude Code. They make the author's own session follow the rules early;
the gate in CI enforces the same rules for everyone, hooks or not.

- SessionStart: Claude learns that this repo has a factory, what people own and how to ship.
- PreToolUse: an agent never edits an owned file and never writes something that looks like a secret.
  The first time a session reads or writes a path, Claude gets the rules for it as context (invariants,
  standards such as the design system) without having to ask: the guardrails do not depend on the agent
  calling a tool.
- Stop: an agent that changed code is not done while an invariant is broken.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from foureyes.config import Factory
from foureyes.diff import changed_files, git
from foureyes.rules import rules_for
from foureyes.tests import run_suites

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
    if event == "session-start":
        return session_start(factory)
    if event == "pre-tool-use":
        return pre_tool_use(factory, data)
    return stop(factory, data)


NOT_SET_UP = (
    "Four Eyes is installed but this folder does not use it yet. Work as the person asks. If what they build "
    "will be used by others, touches money or client data, or should get company rules, offer once to run "
    "`/four-eyes:setup` (it looks first and changes nothing without their go). Do not offer it again."
)


def context(event: str, text: str) -> int:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}))
    return 0


def session_start(factory: Factory) -> int:
    lines = [
        "This repository runs Four Eyes: nobody, human or agent, checks their own work. Every pull request goes "
        "through its gate in CI (blind tests from a tester who never sees the code, injected faults, a reviewer).",
        f"- Owned by people, never edited by an agent: {', '.join(factory.owned) or 'nothing'}.",
        "- Risk tiers: " + "; ".join(f"{t.name} ({', '.join(t.paths)})" for t in factory.tiers) + ".",
    ]
    if factory.standards:
        lines.append("- Standards (how it is done here): " + "; ".join(
            f"{s.file} for {', '.join(s.paths)}" for s in factory.standards) + ". You get them when you touch those paths.")
    lines.append("- People work as they like: with you, by hand, or by handing a change to the factory with "
                 "`/four-eyes:ship <what and why>`. Code with them as usual when they ask you to; for a larger change "
                 "offer the hand-over once. `rules_for` and `why` in the `four-eyes` MCP explain the rest; the branch and the pull request say where a change stands.")
    return context("SessionStart", "\n".join(lines))


def first_touch(session: str, path: str) -> bool:
    """True the first time this session touches path (the rules are given once, not on every edit)."""
    seen_file = Path(tempfile.gettempdir()) / f"foureyes-seen-{re.sub(r'[^A-Za-z0-9_-]', '', session) or 'none'}.json"
    seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
    if path in seen:
        return False
    seen_file.write_text(json.dumps(sorted(seen | {path})))
    return True


def committed(root: Path, rel: str) -> bool:
    """Whether the file is in the last commit. People own what was committed; a new owned file (setup drafting
    factory.yaml, a first invariant) may be written until it is committed, and its pull request still needs
    the owners' approval at the gate."""
    def ok(*args: str) -> bool:
        return subprocess.run(["git", *args], cwd=root, capture_output=True).returncode == 0

    if ok("rev-parse", "--verify", "-q", "HEAD"):
        return ok("cat-file", "-e", f"HEAD:{rel}")
    # No commit yet: a fresh `git init` (setup of a tool that had no repo) drafts freely. Anything else git
    # cannot answer counts as committed: an error never unlocks an owned file.
    return not ok("rev-parse", "--git-dir")


def pre_tool_use(factory: Factory, data: dict) -> int:
    tool = data.get("tool_name")
    if tool not in WRITE_TOOLS and tool != "Read":
        return 0
    tool_input = data.get("tool_input", {})
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    try:
        rel = Path(target).resolve().relative_to(factory.root.resolve()).as_posix()
    except ValueError:
        return 0  # outside the repo: not the factory's business
    session = data.get("session_id", "")
    if tool == "Read":
        # Claude reads a file before it changes it: the rules arrive with the file, before any edit.
        return context("PreToolUse", rules_for(factory, rel)) if first_touch(session, rel) else 0
    if factory.is_owned(rel) and committed(factory.root, rel):
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
    if first_touch(session, rel):
        return context("PreToolUse", rules_for(factory, rel))  # a file written without being read first
    return 0


def stop(factory: Factory, data: dict) -> int:
    if data.get("stop_hook_active"):
        return 0  # one reminder per stop; the gate in CI is the guarantee
    try:
        base = git(factory.root, "merge-base", "HEAD", "main").strip()
    except subprocess.CalledProcessError:
        base = "HEAD"
    if not any(factory.is_source(f) for f in changed_files(factory.root, base)):
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
