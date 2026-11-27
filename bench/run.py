"""FourEyes on someone else's code.

Ten bugs fixed in python-humanize in 2026, after the models' training data, so no model can remember the fix.
For each bug: the code as it was before the fix, the bug written as a plain issue (symptom and example, no hint
of the fix, see bench/issues), and the autopilot with nothing else. Then four questions:

  fixed      do the maintainers' own regression tests (hidden from the factory) pass on the autopilot's code?
  tester     do the blind tester's tests fail on the buggy code, so they would have caught the bug?
  author     do the author's own new tests fail on the buggy code?
  agrees     do the blind tests pass on the maintainers' fix (or do they demand something else)?

Run: uv run python bench/run.py [pr numbers]   (needs `claude` signed in, gh, and bench/work set up as below)
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "bench" / "work"
REPO = WORK / "humanize"
PY = WORK / "venv" / "bin" / "python"
FOUREYES = ROOT / ".venv" / "bin" / "foureyes"
UPSTREAM = "python-humanize/humanize"
SKIPPED_TESTS = ["tests/test_i18n.py", "tests/test_benchmarks.py"]  # need compiled catalogs / a plugin; no bug here

FACTORY = f"""# FourEyes on python-humanize (bench setup)
owned: [factory.yaml]
source: src
test_command: {PY} -m pytest
python: {PY}
suites:
  author: tests
  tester: tests/blind
  invariants: tests/invariants
tiers:
  money:
    paths: ["src/**"]
    mutation_min: 0.8
  low:
    paths: ["**"]
    mutation_min: 0.0
"""


def sh(*cmd, cwd=None, check=True) -> str:
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True).stdout


def tree(ref: str) -> Path:
    """A throwaway copy of the upstream repo at ref, importable from source."""
    dest = Path(tempfile.mkdtemp(prefix="bench-"))
    sh("git", "worktree", "add", "-q", "--detach", str(dest / "t"), ref, cwd=REPO)
    t = dest / "t"
    (t / "src/humanize/_version.py").write_text('__version__ = "0.0.0"\n')
    return t


def drop(t: Path) -> None:
    sh("git", "worktree", "remove", "--force", str(t), cwd=REPO, check=False)
    shutil.rmtree(t.parent, ignore_errors=True)


def failures(t: Path, files: list[str]) -> int | None:
    """How many tests in files fail in tree t; None when they cannot even be collected."""
    files = [f for f in files if (t / f).exists()]
    if not files:
        return 0
    out = subprocess.run(
        [str(PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
        cwd=t, capture_output=True, text=True, env={"PYTHONPATH": str(t / "src"), "PATH": "/usr/bin:/bin"},
    )
    if out.returncode in (2, 3, 4):  # interrupted: the tests do not even collect
        return None
    counts = re.findall(r"(\d+) (failed|error)", out.stdout)
    return sum(int(c) for c, _ in counts)


def overlay(t: Path, src: Path | str, files: list[str], ref: str | None = None) -> None:
    for f in files:
        (t / f).parent.mkdir(parents=True, exist_ok=True)
        if ref:
            (t / f).write_text(sh("git", "show", f"{ref}:{f}", cwd=REPO))
        else:
            shutil.copy2(Path(src) / f, t / f)


def setup(n: int) -> tuple[Path, str, str]:
    merge = json.loads(sh("gh", "pr", "view", str(n), "--repo", UPSTREAM, "--json", "mergeCommit"))["mergeCommit"]["oid"]
    sh("git", "fetch", "-q", "origin", merge, cwd=REPO, check=False)
    wt = WORK / f"pr{n}"
    if wt.exists():
        sh("git", "worktree", "remove", "--force", str(wt), cwd=REPO, check=False)
        shutil.rmtree(wt, ignore_errors=True)
    sh("git", "worktree", "prune", cwd=REPO)
    # A rerun starts from nothing: the autopilot would otherwise go on with the last run's branch.
    for branch in sh("git", "branch", "--list", f"factory/pr{n}-*", "--format=%(refname:short)", cwd=REPO).split():
        sh("git", "branch", "-D", branch, cwd=REPO)
    sh("git", "worktree", "add", "-q", "--detach", str(wt), f"{merge}^1", cwd=REPO)
    sh("git", "checkout", "-q", "-B", f"bench-main-{n}", cwd=wt)
    sh("git", "branch", "-f", "main", "HEAD", cwd=wt, check=False)
    (wt / "factory.yaml").write_text(FACTORY)
    (wt / "src/humanize/_version.py").write_text('__version__ = "0.0.0"\n')
    for f in SKIPPED_TESTS:
        (wt / f).unlink(missing_ok=True)
    sh("git", "add", "-A", cwd=wt)
    sh("git", "add", "-f", "src/humanize/_version.py", cwd=wt)
    sh("git", "-c", "user.name=bench", "-c", "user.email=bench@four-eyes.local", "commit", "-q", "-m", "bench setup", cwd=wt)
    return wt, merge, sh("git", "rev-parse", "HEAD", cwd=wt).strip()


def one(issue: Path) -> dict:
    n = int(re.match(r"pr(\d+)", issue.stem).group(1))
    wt, merge, setup_sha = setup(n)
    log = WORK / f"pr{n}.log"
    with log.open("w") as fh:
        subprocess.run([str(FOUREYES), "autopilot", str(issue)], cwd=wt, stdout=fh, stderr=subprocess.STDOUT)
    slug = issue.stem
    run_file = wt / ".factory" / "runs" / f"{slug}.json"
    run = json.loads(run_file.read_text()) if run_file.exists() else {}
    head = sh("git", "rev-parse", "HEAD", cwd=wt).strip()

    changed = sh("git", "diff", "--name-only", f"{merge}^1", merge, cwd=REPO).split()
    hidden = [f for f in changed if f.startswith("tests/")]
    ours = sh("git", "diff", "--name-only", setup_sha, head, cwd=wt).split()
    blind = [f for f in ours if f.startswith("tests/blind/") and f.endswith(".py")]
    author = [f for f in ours if f.startswith("tests/") and not f.startswith("tests/blind/") and f.endswith(".py")]

    result = {"pr": n, "issue": slug, "cost_usd": run.get("cost_usd"), "minutes": run.get("minutes"),
              "gate_passed": run.get("passed"), "blind_files": blind, "author_files": author}

    t = tree(head)  # the autopilot's code with the maintainers' tests
    try:
        overlay(t, None, hidden, ref=merge)
        f = failures(t, hidden)
        result["fixed"] = f == 0
        result["hidden_failures"] = f
    finally:
        drop(t)
    t = tree(f"{merge}^1")  # the buggy code
    try:
        overlay(t, None, hidden, ref=merge)
        result["hidden_fail_on_buggy"] = bool(failures(t, hidden))
        overlay(t, None, hidden, ref=f"{merge}^1")  # back to the buggy version's own tests
        overlay(t, wt, blind)
        result["tester_caught"] = bool(failures(t, blind))
        overlay(t, wt, author)
        result["author_caught"] = bool(failures(t, author))
    finally:
        drop(t)
    t = tree(merge)  # the maintainers' fix
    try:
        overlay(t, wt, blind)
        f = failures(t, blind)
        result["tester_agrees_with_maintainers"] = f == 0
        result["tester_disagreements"] = f
    finally:
        drop(t)
    print(json.dumps(result), flush=True)
    return result


def summary(results: list[dict]) -> str:
    n = len(results)

    def count(k):
        return sum(1 for r in results if r.get(k))

    lines = [
        "# FourEyes on someone else's code\n",
        f"{n} bugs fixed in [python-humanize](https://github.com/{UPSTREAM}) in 2026, after the models' training data. "
        "For each: the code before the fix, the bug as a plain issue (symptom and example, no hint of the fix: "
        "[bench/issues](../bench/issues)), and the autopilot with nothing else. The maintainers' own regression tests "
        "were hidden from the factory and used only to judge.\n",
        "| | |", "|---|---|",
        f"| **Fixed** (the maintainers' hidden tests pass on the autopilot's code) | **{count('fixed')} of {n}** |",
        f"| Blind tester's tests fail on the buggy code (would have caught it) | {count('tester_caught')} of {n} |",
        f"| Author's own tests fail on the buggy code | {count('author_caught')} of {n} |",
        f"| Blind tests agree with the maintainers' fix | {count('tester_agrees_with_maintainers')} of {n} |",
        f"| The gate passed | {count('gate_passed')} of {n} |",
        "",
        "| Bug | Fixed | Tester caught | Author caught | Tester agrees | Minutes | Cost |",
        "|---|---|---|---|---|---|---|",
    ]
    yes = {True: "yes", False: "no", None: "?"}
    for r in sorted(results, key=lambda r: r["pr"]):
        lines.append(
            f"| [#{r['pr']}](https://github.com/{UPSTREAM}/pull/{r['pr']}) {r['issue'].split('-', 1)[1]} "
            f"| {yes[r.get('fixed')]} | {yes[r.get('tester_caught')]} | {yes[r.get('author_caught')]} "
            f"| {yes[r.get('tester_agrees_with_maintainers')]} | {r.get('minutes') or '?'} | ${r.get('cost_usd') or 0:.2f} |"
        )
    cost = sum(r.get("cost_usd") or 0 for r in results)
    lines += ["", f"Total cost ${cost:.2f}."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    wanted = {int(a) for a in sys.argv[1:]}
    issues = sorted(p for p in (ROOT / "bench" / "issues").glob("pr*.md")
                    if not wanted or int(re.match(r"pr(\d+)", p.stem).group(1)) in wanted)
    with ThreadPoolExecutor(max_workers=3) as pool:
        fresh = list(pool.map(one, issues))
    # A rerun of some bugs replaces only their rows; the others keep their last result.
    saved = ROOT / "bench" / "results.json"
    by_pr = {r["pr"]: r for r in (json.loads(saved.read_text()) if saved.exists() else [])}
    by_pr.update({r["pr"]: r for r in fresh})
    results = sorted(by_pr.values(), key=lambda r: r["pr"])
    saved.write_text(json.dumps(results, indent=2))
    (ROOT / "docs" / "bench.md").write_text(summary(results))
    print(summary(results))
