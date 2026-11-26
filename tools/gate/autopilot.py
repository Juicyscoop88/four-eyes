"""Autopilot: a person writes the issue, the factory does the rest.

plan (author) -> blind tests (tester) -> code (author, under the hooks) -> gate
  -> until the score is met: surviving faults, in words, back to the tester (via the reviewer)
  -> a proposal for the owners when the invariants do not cover the change
  -> the reviewer's decision cards -> the merge request (here: a branch and its report)

Every step is a commit by its role, so the history says who did what. A person can take the wheel at any
commit: check out the branch, go on by hand, run the gate.
"""

import json
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from gate import agents, mutation
from gate.check import check, facts, report
from gate.config import Factory
from gate.diff import changed_lines, diff_text, git
from gate.tests import checkout_copy, run_suites


class Pilot:
    def __init__(self, factory: Factory, issue_path: Path, log=print):
        self.f, self.log = factory, log
        self.slug = issue_path.stem
        self.name = self.slug.replace("-", "_")
        self.issue = issue_path.read_text()
        self.task_path = f".factory/tasks/{self.slug}.md"
        self.requested_by = git(factory.root, "config", "user.name").strip() or "unknown"
        self.runs: list[agents.AgentRun] = []
        self.steps: list[dict] = []
        self.started = time.monotonic()

    # ---- helpers ------------------------------------------------------------------------

    def task(self) -> str:
        return (self.f.root / self.task_path).read_text()

    def commit(self, role: str, message: str) -> None:
        root = self.f.root
        git(root, "add", "-A")
        if not git(root, "status", "--porcelain").strip():
            return
        subprocess.run(
            ["git", "-c", f"user.name={role} agent", "-c", f"user.email={role}@four-eyes.local",
             "commit", "-q", "-m", f"{message}\n\nFactory-Role: {role}\nRequested-by: {self.requested_by}"],
            cwd=root, check=True,
        )

    def step(self, what: str, run: agents.AgentRun | None = None, **extra) -> None:
        if run:
            self.runs.append(run)
        entry = {"step": what, **({"role": run.role, "cost_usd": run.cost_usd, "seconds": run.seconds} if run else {}), **extra}
        self.steps.append(entry)
        cost = f" (${run.cost_usd:.3f}, {run.seconds:.0f} s)" if run else ""
        self.log(f"autopilot: {what}{cost}")

    # ---- the path -----------------------------------------------------------------------

    def run(self, max_rounds: int = 4) -> Path:
        root = self.f.root
        if git(root, "status", "--porcelain").strip():
            raise SystemExit("autopilot: the working tree is not clean")
        branch = f"factory/{self.slug}"
        if git(root, "branch", "--list", branch).strip():
            # Handing it back: someone took the wheel on this branch, the factory goes on from there.
            git(root, "checkout", "-q", branch)
            self.base = git(root, "merge-base", "HEAD", "main").strip()
            self.step("continue on the existing branch")
        else:
            self.base = git(root, "rev-parse", "HEAD").strip()
            git(root, "checkout", "-q", "-b", branch)
            self.plan()
            run, written = agents.write_blind_tests(self.f, self.task(), self.name)
            self.commit("tester", f"Blind tests for {self.slug} (the tester never saw an implementation)")
            self.step("blind tests", run, files=written)
            self.step("implementation", agents.author(self.f, (
                f"Implement the task in `{self.task_path}`. The tester's tests for it are in "
                f"`{self.f.suites['tester']}/` (read them, never edit them). Write your own tests in "
                f"`{self.f.suites['author']}/`. Run `uv run pytest` until everything is green."
            )))
            self.commit("author", f"Implement {self.slug}")

        equivalent: dict[str, str] = {}
        for rnd in range(1, max_rounds + 1):
            res = check(self.f, self.base, self.task(), False, equivalent, log=lambda m: None)
            if res.failures:
                self.step(f"round {rnd}: {len(res.failures)} tests fail, back to the author")
                self.step("fix", agents.author(self.f, (
                    f"The task is in `{self.task_path}`. The gate found failing tests:\n\n{facts(res)}\n\n"
                    "Fix the code. Never edit the tester's tests or owned files; if a test contradicts the "
                    "task, say so in your final answer instead."
                )))
                self.commit("author", f"Fix what the gate found ({self.slug}, round {rnd})")
                continue
            self.step(f"round {rnd}: score {res.score:.0%}, {len(res.survivors)} faults survived",
                      score=res.score, survivors=len(res.survivors))
            if not res.survivors:
                break
            gaps = agents.explain_gaps(self.f, self.task(), diff_text(root, self.base),
                                       [f"{m.id}: {m.path}:{m.line} {m.description}" for m in res.survivors])
            for g in gaps.gaps:
                if g.get("equivalent"):
                    equivalent[g["id"]] = g.get("why", "")
            behaviors = [g["behavior"] for g in gaps.gaps if not g.get("equivalent") and g.get("behavior")]
            self.step(f"reviewer turns {len(res.survivors)} survivors into {len(behaviors)} behaviors to test",
                      gaps.run, equivalent=[g["id"] for g in gaps.gaps if g.get("equivalent")])
            if behaviors:
                run, written = agents.write_blind_tests(self.f, self.task(), self.name, behaviors)
                self.commit("tester", f"Blind tests for what the gate found untested ({self.slug}, round {rnd})")
                self.step("tester adds tests, blind again", run, files=written)

        final = check(self.f, self.base, self.task(), False, equivalent, log=lambda m: None)
        proposal = self.propose(final) if final.counted and final.caught("invariants") < len(final.counted) / 2 else None

        final = check(self.f, self.base, self.task(), True, equivalent, log=lambda m: None)
        final.proposal = proposal
        final.agent_runs = self.runs + final.agent_runs
        self.step("gate with the reviewer: " + ("passed" if final.passed else "blocked"), final.review.run if final.review else None)

        out = root / ".factory" / "runs"
        out.mkdir(parents=True, exist_ok=True)
        text = report(self.f, final, git(root, "rev-parse", "HEAD").strip())
        (out / f"{self.slug}.md").write_text(text)
        (root / "gate-report.md").write_text(text)
        (out / f"{self.slug}.json").write_text(json.dumps({
            "issue": self.slug, "requested_by": self.requested_by, "passed": final.passed,
            "score": final.score, "mutants": len(final.counted), "equivalent": final.equivalent,
            "caught": {s: final.caught(s) for s in ("author", "tester", "invariants")},
            "proposal": proposal, "cost_usd": round(sum(r.cost_usd for r in final.agent_runs), 3),
            "minutes": round((time.monotonic() - self.started) / 60, 1), "steps": self.steps,
            "cards": final.review.map if final.review else [],
            "findings": final.review.findings if final.review else [],
        }, indent=2))
        self.commit("factory", f"Gate report for {self.slug}: " + ("passed" if final.passed else "blocked"))
        return out / f"{self.slug}.md"

    def plan(self) -> None:
        self.step("plan", agents.author(self.f, (
            f"A person wrote this issue:\n\n{self.issue}\n\n"
            f"Do not implement it yet. Write `{self.task_path}`: the issue in the person's words, then a section "
            "`## Interface` with the exact signatures you will add, then `## Assumptions` for anything the issue "
            "leaves open, with the choice you take (a person will see them). Add the new names to `src/` as stubs "
            "(signature, docstring, `raise NotImplementedError`) and export them where the package exports its "
            "other functions. Write no tests and no implementation."
        )))
        self.commit("author", f"Plan {self.slug}: the task and its interface")

    def propose(self, res) -> dict | None:
        existing = sorted((self.f.root / ".factory" / "proposals" / self.slug).rglob("*.py"))
        if existing:
            folder = self.f.root / ".factory" / "proposals" / self.slug
            path, text = existing[0].relative_to(folder).as_posix(), existing[0].read_text()
        else:
            run, proposals = agents.propose_invariant_tests(self.f, self.task(), self.name)
            self.step("tester proposes an extension of the owned invariant tests", run)
            if not proposals:
                return None
            path, text = next(iter(proposals.items()))
        work = checkout_copy(self.f.root)
        try:
            (work / path).write_text(text)
            failures, _ = run_suites(self.f, work, only=("invariants",))
            if failures:
                self.step("the proposal fails on the current code, dropped", failures=[f.message for f in failures][:3])
                return None
            targets = {f: changed_lines(self.f.root, self.base, f) for f in res.files
                       if f.startswith("src/") and f.endswith(".py") and (self.f.root / f).exists()}
            after = [m for m in mutation.run(self.f, work, targets) if m.id not in res.equivalent]
        finally:
            shutil.rmtree(work, ignore_errors=True)
        dest = f".factory/proposals/{self.slug}/{path}"
        (self.f.root / dest).parent.mkdir(parents=True, exist_ok=True)
        (self.f.root / dest).write_text(text)
        self.commit("tester", f"Proposal for the owners: invariant tests that cover {self.slug}")
        caught = sum(1 for m in after if "invariants" in m.caught_by)
        return {"file": dest, "target": path, "before": res.caught("invariants"), "after": caught, "n": len(after)}
