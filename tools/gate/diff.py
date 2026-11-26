"""What a change touches, read from git."""

import re
import subprocess
from pathlib import Path

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def changed_files(root: Path, base: str) -> list[str]:
    """Files changed between base and the working tree, committed or not."""
    out = git(root, "diff", "--name-only", base, "--")
    untracked = git(root, "ls-files", "--others", "--exclude-standard")
    return sorted({*out.split(), *untracked.split()})


def changed_lines(root: Path, base: str, path: str) -> set[int]:
    """Line numbers in the new version of path that the change added or modified."""
    if not git(root, "ls-files", path).strip():
        return set(range(1, len((root / path).read_text().splitlines()) + 1))
    lines: set[int] = set()
    for line in git(root, "diff", "-U0", base, "--", path).splitlines():
        m = HUNK.match(line)
        if m:
            start, count = int(m.group(1)), int(m.group(2) or "1")
            lines.update(range(start, start + count))
    return lines


def diff_text(root: Path, base: str) -> str:
    out = git(root, "diff", base, "--")
    for path in git(root, "ls-files", "--others", "--exclude-standard").split():
        out += subprocess.run(
            ["git", "diff", "--no-index", "/dev/null", path], cwd=root, capture_output=True, text=True
        ).stdout
    return out
