"""The eval: does the factory catch real bugs, and which tester is worth its cost?

For each finished task (a factory/<slug> branch):
- an adversary who sees the code plants k realistic bugs, one edit each;
- each bug runs against every suite: the author's tests, the tester's (on opus, as the factory runs it,
  and on cheaper models writing from scratch), the owned invariants, and the invariants with the
  tester's proposal;
- a bug no test catches goes to the reviewer, the last check before a person;
- the same tester variants are scored by mutation on the changed lines.
"""

import shutil
from pathlib import Path

from gate import agents, mutation
from gate.check import facts, Result
from gate.config import Factory
from gate.diff import changed_files, changed_lines, diff_text, git
from gate.tests import checkout_copy, run_suites


def _apply(root: Path, bug: dict) -> str | None:
    path = root / bug["file"]
    text = path.read_text()
    if text.count(bug["find"]) != 1:
        return None
    path.write_text(text.replace(bug["find"], bug["replace"]))
    return text


def evaluate(factory: Factory, slug: str, k: int, testers: list[str], log=print) -> dict:
    root = factory.root
    git(root, "checkout", "-q", f"factory/{slug}")
    base = git(root, "merge-base", "HEAD", "main").strip()
    task = (root / f".factory/tasks/{slug}.md").read_text()
    name = slug.replace("-", "_")
    src = [f for f in changed_files(root, base) if f.startswith("src/") and f.endswith(".py")]
    targets = {f: changed_lines(root, base, f) for f in src}
    out: dict = {"task": slug, "testers": {}, "bugs": [], "cost_usd": 0.0}
    copies: dict[str, Path] = {}
    try:
        # The tester variants: the factory's own tests, and cheaper models writing from scratch.
        copies[factory.models["tester"]] = checkout_copy(root)
        for model in testers:
            if model == factory.models["tester"]:
                continue
            copy = checkout_copy(root)
            run, _ = agents.write_blind_tests(factory, task, name, model=model, dest_root=copy, fresh=True)
            out["cost_usd"] += run.cost_usd
            copies[model] = copy
            log(f"eval {slug}: tester on {model} wrote its tests (${run.cost_usd:.3f})")
        proposal = sorted((root / ".factory/proposals" / slug).rglob("*.py"))
        with_proposal = None
        if proposal:
            with_proposal = checkout_copy(root)
            rel = proposal[0].relative_to(root / ".factory/proposals" / slug).as_posix()
            shutil.copy2(proposal[0], with_proposal / rel)

        for model, copy in copies.items():
            ms = mutation.run(factory, copy, targets)
            out["testers"][model] = {"mutants": len(ms), "mutation_caught": sum(1 for m in ms if "tester" in m.caught_by)}

        run, bugs = agents.seed_bugs(factory, task, {f: (root / f).read_text() for f in src}, k)
        out["cost_usd"] += run.cost_usd
        log(f"eval {slug}: the adversary planted {len(bugs)} bugs (${run.cost_usd:.3f})")

        for bug in bugs:
            entry = {"file": bug["file"], "why": bug.get("why", ""), "caught_by": {}}
            for label, copy in [*copies.items(), ("proposal", with_proposal)]:
                if copy is None:
                    continue
                original = _apply(copy, bug)
                if original is None:
                    entry["invalid"] = "the edit does not match the code exactly once"
                    break
                failures, _ = run_suites(factory, copy)
                (copy / bug["file"]).write_text(original)
                suites = sorted({f.suite for f in failures})
                if "collection" in suites:
                    entry["invalid"] = "the code no longer imports"
                    break
                if label == factory.models["tester"]:
                    entry["caught_by"]["author"] = "author" in suites
                    entry["caught_by"]["invariants"] = "invariants" in suites
                if label == "proposal":
                    entry["caught_by"]["invariants_with_proposal"] = "invariants" in suites
                else:
                    entry["caught_by"][f"tester_{label}"] = "tester" in suites
            if "invalid" not in entry:
                factory_tests = entry["caught_by"][f"tester_{factory.models['tester']}"] or entry["caught_by"]["invariants"]
                entry["caught_by"]["gate_tests"] = factory_tests
                if not factory_tests:
                    original = _apply(root, bug)
                    try:
                        review = agents.review(factory, task, diff_text(root, base), facts(Result(base, src, "money")))
                    finally:
                        (root / bug["file"]).write_text(original)
                    out["cost_usd"] += review.run.cost_usd
                    entry["caught_by"]["reviewer"] = any(f.get("severity") == "block" for f in review.findings)
                    entry["reviewer_said"] = [f.get("what", "") for f in review.findings][:2]
            out["bugs"].append(entry)
            log(f"eval {slug}: {bug['file']}: {entry.get('invalid') or entry['caught_by']}")
    finally:
        for copy in [*copies.values(), with_proposal if "with_proposal" in dir() else None]:
            if copy:
                shutil.rmtree(copy, ignore_errors=True)
        git(root, "checkout", "-q", "main")
    out["cost_usd"] = round(out["cost_usd"], 3)
    return out


def summary(results: list[dict], testers: list[str]) -> str:
    valid = [b for r in results for b in r["bugs"] if "invalid" not in b]
    n = len(valid)

    def count(key):
        return sum(1 for b in valid if b["caught_by"].get(key))

    lines = [
        "# Eval: planted bugs and tester models\n",
        f"{len(results)} tasks done by the autopilot, {n} realistic bugs planted by an adversary agent that saw "
        "the finished code (invalid edits excluded). Each bug ran against every suite.\n",
        "| Check | Bugs caught |", "|---|---|",
        f"| author's own tests | {count('author')} of {n} |",
    ]
    lines += [f"| tester on {m} (blind) | {count('tester_' + m)} of {n} |" for m in testers]
    lines += [
        f"| owned invariants | {count('invariants')} of {n} |",
        f"| owned invariants with the tester's proposal | {count('invariants_with_proposal')} of {n} |",
        f"| **the gate's tests** (factory tester + invariants) | **{count('gate_tests')} of {n}** |",
        f"| reviewer, on the bugs no test caught | {count('reviewer')} of {n - count('gate_tests')} |",
        "",
        "## Tester models, by mutation on the changed lines\n",
        "| Task | " + " | ".join(testers) + " |",
        "|---|" + "---|" * len(testers),
    ]
    for r in results:
        cells = []
        for m in testers:
            t = r["testers"].get(m)
            cells.append(f"{t['mutation_caught']} of {t['mutants']}" if t else "")
        lines.append(f"| {r['task']} | " + " | ".join(cells) + " |")
    missed = [(r["task"], b) for r in results for b in r["bugs"]
              if "invalid" not in b and not b["caught_by"].get("gate_tests")]
    if missed:
        lines += ["", "## What the gate's tests missed\n"]
        for task, b in missed:
            verdict = "the reviewer blocked it" if b["caught_by"].get("reviewer") else "nobody caught it"
            lines.append(f"- **{task}**, `{b['file']}`: {b['why']} ({verdict})")
    cost = sum(r["cost_usd"] for r in results)
    lines += ["", f"Cost of the eval: ${cost:.2f}."]
    return "\n".join(lines) + "\n"
