"""Run the test suites of a checkout and say which tests of which suite failed."""

import os
import shutil
import subprocess
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
    file: str = ""  # the test's module as a path, so a failure can be matched on another checkout

    @property
    def key(self) -> tuple[str, str]:
        return self.file, self.test


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


def base_copy(root: Path, base: str) -> Path:
    """A throwaway copy of the base revision, to tell a test this change broke from one that was red before it."""
    dest = Path(tempfile.mkdtemp(prefix="gate-base-"))
    archive = subprocess.run(["git", "archive", base], cwd=root, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    return dest


def run_suites(
    factory: Factory, workdir: Path, only: tuple[str, ...] = (), timeout: int = 180, paths: tuple[str, ...] = (),
) -> tuple[list[Failure], int]:
    """Run every suite present in workdir (or only the named ones, or exactly the given test paths).
    Returns the failures and how many tests ran."""
    if paths:
        folders, ignore = [p for p in paths if (workdir / p).exists()], []
    else:
        folders = [f for n, f in factory.suites.items() if (workdir / f).exists() and (not only or n in only)]
        nested = [f for f in factory.suites.values() if any(f != g and f.startswith(g.rstrip("/") + "/") for g in folders)]
        ignore = [f"--ignore={f}" for f in nested if f not in folders]
        folders = [f for f in folders if not any(f != g and f.startswith(g.rstrip("/") + "/") for g in folders)]
    if not folders:
        return [], 0
    report = workdir / ".gate-junit.xml"
    env = {**os.environ, "PYTHONPATH": str(workdir / factory.source), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        subprocess.run(
            [factory.python, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", *ignore, *folders],
            cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [Failure("timeout", "all", f"tests did not finish in {timeout} s")], 0
    if not report.exists():
        return [Failure("collection", "all", f"pytest wrote no report: is pytest installed for {factory.python}?")], 0
    failures, total = [], 0
    for case in ET.parse(report).getroot().iter("testcase"):
        total += 1
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        path = case.get("classname", "").replace(".", "/")
        suite = factory.suite_of(path + ".py") or "other"
        message = (problem.get("message") or problem.text or "").strip().splitlines()
        failures.append(Failure(suite, case.get("name", "?"), message[0] if message else "", path + ".py"))
    report.unlink()
    return failures, total
