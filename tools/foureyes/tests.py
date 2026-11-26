"""Run the test suites of a checkout and say which tests of which suite failed."""

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from foureyes.config import Factory
from foureyes.diff import git


@dataclass(frozen=True)
class Failure:
    suite: str
    test: str
    message: str


def checkout_copy(root: Path) -> Path:
    """A throwaway copy of the working tree: tracked and untracked files, no build output."""
    dest = Path(tempfile.mkdtemp(prefix="gate-"))
    files = git(root, "ls-files", "--cached", "--others", "--exclude-standard").split()
    for f in files:
        src = root / f
        if src.is_file():
            (dest / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / f)
    return dest


def run_suites(
    factory: Factory, workdir: Path, only: tuple[str, ...] = (), timeout: int = 180
) -> tuple[list[Failure], int]:
    """Run every suite present in workdir (or only the named ones). Returns the failures and how many tests ran."""
    folders = [f for n, f in factory.suites.items() if (workdir / f).exists() and (not only or n in only)]
    if not folders:
        return [], 0
    report = workdir / ".gate-junit.xml"
    env = {**os.environ, "PYTHONPATH": str(workdir / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", *folders],
            cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [Failure("timeout", "all", f"tests did not finish in {timeout} s")], 0
    if not report.exists():
        return [Failure("collection", "all", "pytest wrote no report")], 0
    failures, total = [], 0
    for case in ET.parse(report).getroot().iter("testcase"):
        total += 1
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        path = case.get("classname", "").replace(".", "/")
        suite = next((n for n, f in factory.suites.items() if path.startswith(f.rstrip("/"))), "other")
        message = (problem.get("message") or problem.text or "").strip().splitlines()
        failures.append(Failure(suite, case.get("name", "?"), message[0] if message else ""))
    report.unlink()
    return failures, total
