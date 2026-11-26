"""Why does this line exist? Issue, who asked, which decision, which tests pin it, who approved.

Everything comes from what the factory already records: commits by role with their trailers, the task
file with its decisions, the tests (found by breaking the line and seeing which fail), and the pull request.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from gate import mutation
from gate.config import Factory
from gate.diff import git
from gate.tests import checkout_copy, run_suites


def _trailers(message: str) -> dict[str, str]:
    return dict(re.findall(r"^([A-Z][A-Za-z-]+): (.+)$", message, re.M))


def _task_of(root: Path, sha: str) -> str | None:
    for name in git(root, "log", sha, "-n", "60", "--name-only", "--format=").split():
        if name.startswith(".factory/tasks/") and name.endswith(".md"):
            return name
    return None


def _pull_request(root: Path, sha: str) -> str | None:
    try:
        url = git(root, "remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return None
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not m or not shutil.which("gh"):
        return None
    repo = m.group(1)
    out = subprocess.run(["gh", "api", f"repos/{repo}/commits/{sha}/pulls"], capture_output=True, text=True)
    if out.returncode != 0 or not json.loads(out.stdout or "[]"):
        return None
    pr = json.loads(out.stdout)[0]
    reviews = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{pr['number']}/reviews"], capture_output=True, text=True)
    approved = sorted({r["user"]["login"] for r in json.loads(reviews.stdout or "[]") if r["state"] == "APPROVED"})
    state = "merged" if pr.get("merged_at") else pr["state"]
    who = f"approved by {', '.join(approved)}" if approved else "not approved yet"
    return f"[#{pr['number']} {pr['title']}]({pr['html_url']}), {state}, {who}"


def why(factory: Factory, path: str, line: int) -> str:
    root = factory.root
    blame = git(root, "blame", "-L", f"{line},{line}", "--porcelain", "--", path)
    sha = blame.split()[0]
    code = next((ln[1:] for ln in blame.splitlines() if ln.startswith("\t")), "").strip()
    message = git(root, "log", "-1", "--format=%B", sha)
    author = git(root, "log", "-1", "--format=%an, %ad", "--date=short", sha).strip()
    trailers = _trailers(message)

    out = [f"# Why `{path}:{line}` exists\n", f"```python\n{code}\n```\n"]
    out.append(f"- **Written by:** {author}, in `{sha[:10]}` *{message.splitlines()[0]}*")
    if "Requested-by" in trailers:
        out.append(f"- **Asked for by:** {trailers['Requested-by']}")

    task = _task_of(root, sha)
    if task and (root / task).exists():
        text = (root / task).read_text()
        out.append(f"- **The task:** `{task}`, *{text.splitlines()[0].lstrip('# ').strip()}*")
        decisions = text.split("## Decisions", 1)[1].strip().splitlines() if "## Decisions" in text else []
        if decisions:
            out.append("- **Decisions made by people on it:**")
            out += [f"  {d.strip()}" for d in decisions if d.strip()]

    # The tests that pin this line: break it in every way the gate knows, see which tests fail.
    mutants = mutation.mutants_of(path, (root / path).read_text(), {line})
    pinned: dict[str, set[str]] = {}
    if mutants:
        work = checkout_copy(root)
        try:
            for m in mutants:
                (work / path).write_text(m.source)
                failures, _ = run_suites(factory, work)
                for f in failures:
                    pinned.setdefault(f.suite, set()).add(f.test.split("[")[0])
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if pinned:
            out.append(f"- **Pinned by tests** (each fails when this line is broken, {len(mutants)} ways tried):")
            for suite in ("invariants", "tester", "author"):
                if suite in pinned:
                    names = sorted(pinned[suite])
                    more = f" and {len(names) - 4} more" if len(names) > 4 else ""
                    out.append(f"  - {suite}: {', '.join(f'`{n}`' for n in names[:4])}{more}")
        else:
            out.append(f"- **No test fails when this line is broken** ({len(mutants)} way{"s" if len(mutants) != 1 else ""} tried): nothing pins it.")
    pr = _pull_request(root, sha)
    if pr:
        out.append(f"- **Pull request:** {pr}")
    return "\n".join(out) + "\n"
