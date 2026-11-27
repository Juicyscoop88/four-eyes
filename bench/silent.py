"""Silent failures: does FourEyes stop a wrong fix that plain Claude Code calls done?

Plain Claude Code fixes bugs about as well as the autopilot, so counting fixes says nothing. What a factory
adds is knowing when a fix is wrong although the agent says it is done. For each bug of the bench:

  1. plain Claude Code (the author's model, the issue only, may run the tests) fixes it, as an engineer's
     agent would today;
  2. the maintainers' hidden regression tests judge whether the fix is right;
  3. FourEyes checks that same change as it would any pull request: the blind tester writes tests from the
     issue alone, then the gate with the reviewer gives its verdict.

Four outcomes: wrong and blocked (a silent failure stopped), wrong and passed (missed), right and passed,
right and blocked (a false alarm: a person is asked for nothing).

Run: uv run python bench/silent.py [pr numbers]
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run as bench  # noqa: E402
from foureyes import agents  # noqa: E402
from foureyes.check import check  # noqa: E402
from foureyes.config import load  # noqa: E402

ROOT = bench.ROOT
OUT = ROOT / "bench" / ("silent.json" if bench.NAME == "humanize" else f"silent-{bench.NAME}.json")


def plain_claude(wt: Path, issue: str, model: str) -> dict:
    """Claude Code as an engineer runs it today: the issue, the repo, the tests. Hermetic like the factory."""
    test = f"{bench.PY} -m pytest"
    prompt = (
        f"Fix this bug in the repository.\n\n{issue}\n\n"
        f"Run the tests with `{test}`. Add a regression test where the project keeps its tests. "
        "When you are done, say so in one sentence."
    )
    cmd = [
        "claude", "-p", prompt, "--model", model, "--tools", "Read,Glob,Grep,Write,Edit,Bash",
        "--allowedTools", f"Bash({test}:*)", "--permission-mode", "acceptEdits", "--output-format", "json",
        "--no-session-persistence", "--setting-sources", "project", "--strict-mcp-config",
    ]
    started = time.monotonic()
    out = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, timeout=1500,
                         env={**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
    data = json.loads(out.stdout) if out.stdout.strip().startswith("{") else {}
    return {"said": data.get("result", out.stderr)[-400:], "cost_usd": data.get("total_cost_usd", 0.0),
            "minutes": round((time.monotonic() - started) / 60, 1)}


def one(issue_file: Path) -> dict:
    n = int(issue_file.stem[2:].split("-")[0])
    wt, merge, setup_sha = bench.setup(n, prefix="plain")
    issue = issue_file.read_text()
    factory = load(wt)
    r = {"pr": n, "issue": issue_file.stem}

    r["plain"] = plain_claude(wt, issue, factory.models["author"])
    bench.sh("git", "add", "-A", cwd=wt)
    bench.sh("git", "-c", "user.name=plain", "-c", "user.email=plain@four-eyes.local",
             "commit", "-q", "-m", "Plain Claude Code's fix", cwd=wt, check=False)
    head = bench.sh("git", "rev-parse", "HEAD", cwd=wt).strip()

    changed = bench.sh("git", "diff", "--name-only", f"{merge}^1", merge, cwd=bench.REPO).split()
    hidden = [f for f in changed if f.startswith("tests/")]
    t = bench.tree(head, wt)
    try:
        bench.overlay(t, None, hidden, ref=merge)
        f = bench.failures(t, hidden)
        r["right"] = f == 0
        r["hidden_failures"] = f
    finally:
        bench.drop(t)

    # FourEyes on that same change, as on any pull request: blind tests from the issue, then the gate.
    tester, written = agents.write_blind_tests(factory, issue, issue_file.stem.replace("-", "_"))
    bench.sh("git", "add", "-A", cwd=wt)
    bench.sh("git", "-c", "user.name=tester", "-c", "user.email=tester@four-eyes.local",
             "commit", "-q", "-m", "Blind tests", cwd=wt, check=False)
    res = check(factory, setup_sha, issue, True, log=lambda m: None)
    r["gate_passed"] = res.passed
    r["blocks"] = res.blocks
    r["cards"] = [c.get("question", "") for c in res.cards()]
    r["factory_cost_usd"] = round(tester.cost_usd + sum(a.cost_usd for a in res.agent_runs), 3)
    r["outcome"] = {(False, False): "stopped", (False, True): "missed",
                    (True, True): "passed", (True, False): "false alarm"}[(r["right"], r["gate_passed"])]
    print(json.dumps(r), flush=True)
    return r


def summary(results: list[dict]) -> str:
    count = {k: sum(1 for r in results if r["outcome"] == k) for k in ("stopped", "missed", "passed", "false alarm")}
    wrong = count["stopped"] + count["missed"]
    lines = [
        "# Silent failures: plain Claude Code, then FourEyes on its fix\n",
        "Plain Claude Code (the author's model, the issue only, may run the tests) fixed each bug and said it was "
        "done. The maintainers' hidden tests judged the fix; FourEyes checked the same change as any pull request.\n",
        "| | Gate blocked | Gate passed |", "|---|---|---|",
        f"| **Fix wrong** (hidden tests fail) | **{count['stopped']} stopped** | {count['missed']} missed |",
        f"| Fix right | {count['false alarm']} false alarm | {count['passed']} passed |",
        "",
        f"Plain Claude Code's fix was wrong in {wrong} of {len(results)} bugs, and said done every time.",
        "",
        "| Bug | Fix right | Gate | Why it blocked |", "|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: r["pr"]):
        why = "; ".join(r["blocks"])[:160] or "-"
        lines.append(f"| #{r['pr']} {r['issue'].split('-', 1)[1]} | {'yes' if r['right'] else 'no'} "
                     f"| {'passed' if r['gate_passed'] else 'blocked'} | {why} |")
    cost = sum(r["plain"]["cost_usd"] + r["factory_cost_usd"] for r in results)
    lines += ["", f"Total cost ${cost:.2f}."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    wanted = {int(a) for a in sys.argv[1:]}
    issues = sorted(p for p in bench.ISSUES.glob("pr*.md")
                    if not wanted or int(p.stem[2:].split("-")[0]) in wanted)
    with ThreadPoolExecutor(max_workers=3) as pool:
        fresh = list(pool.map(one, issues))
    by_pr = {r["pr"]: r for r in (json.loads(OUT.read_text()) if OUT.exists() else [])}
    by_pr.update({r["pr"]: r for r in fresh})
    results = sorted(by_pr.values(), key=lambda r: r["pr"])
    OUT.write_text(json.dumps(results, indent=2))
    (ROOT / "docs" / ("silent.md" if bench.NAME == "humanize" else f"silent-{bench.NAME}.md")).write_text(summary(results))
    print(summary(results))
