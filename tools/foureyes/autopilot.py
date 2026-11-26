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
from pathlib import Path

from foureyes import agents, mutation
from foureyes.check import author_of, check, facts, report
from foureyes.config import Factory
from foureyes.diff import changed_lines, diff_text, git
from foureyes.tests import checkout_copy, run_suites


class Pilot:
    def __init__(self, factory: Factory, issue_path: Path, log=print):
        self.f, self.log = factory, log
        self.slug = issue_path.stem
        self.name = self.slug.replace("-", "_")
        self.issue = issue_path.read_text() if issue_path.exists() else ""
        self.task_path = f".factory/tasks/{self.slug}.md"
        self.requested_by = author_of(factory.root)
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
                f"`{self.f.suites['author']}/`. Run `{self.f.test_command}` until everything is green."
            )))
            self.commit("author", f"Implement {self.slug}")

        return self.finish(self.close_gaps({}, max_rounds))

    def close_gaps(self, equivalent: dict[str, str], max_rounds: int) -> dict[str, str]:
        """Until the score is met: failing tests back to the author, surviving faults (in words) to the tester."""
        root = self.f.root
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
        return equivalent

    def finish(self, equivalent: dict[str, str]) -> Path:
        root = self.f.root
        final = check(self.f, self.base, self.task(), False, equivalent, log=lambda m: None)
        uncovered = final.counted and final.caught("invariants") < len(final.counted) / 2
        proposal = self.propose(final) if self.f.invariants and uncovered else None

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
            "base": self.base,
            "caught": {s: final.caught(s) for s in ("author", "tester", "invariants")},
            "proposal": proposal, "cost_usd": round(sum(r.cost_usd for r in final.agent_runs), 3),
            "minutes": round((time.monotonic() - self.started) / 60, 1), "steps": self.steps,
            "cards": final.cards(),
            "findings": final.review.findings if final.review else [],
        }, indent=2))
        self.commit("factory", f"Gate report for {self.slug}: " + ("passed" if final.passed else "blocked"))
        return out / f"{self.slug}.md"

    def decide(self, card: str, answer: str, decided_by: str, cards: list[dict] | None = None, max_rounds: int = 4) -> Path:
        """A person answered a decision card. The answer becomes a blind test first, then code.

        cards: the cards as the person saw them (from the gate's last comment); else the autopilot's own."""
        root = self.f.root
        git(root, "checkout", "-q", f"factory/{self.slug}")
        record = json.loads((root / ".factory" / "runs" / f"{self.slug}.json").read_text())
        self.base = git(root, "merge-base", "HEAD", "main").strip()
        pool = cards or record["cards"]
        q = next((c for c in pool if c.get("id") == card), None)
        if q is None and card.isdigit() and "id" not in pool[0]:
            q = pool[int(card) - 1]  # cards recorded before they had ids
        if q is None:
            raise SystemExit(f"decide: no card {card}")
        chosen = next((o for o in q.get("options", []) if o == answer or o.split(":")[0].strip() == answer), answer)
        question = q.get("question") or q["why"]
        task = (root / self.task_path).read_text().rstrip()
        if "## Decisions" not in task:
            task += "\n\n## Decisions\n"
        (root / self.task_path).write_text(f"{task}\n- **{question}** {chosen} (decided by {decided_by})\n")
        self.commit("factory", f"Decision by {decided_by}: {question}\n\nAnswer: {chosen}\nDecided-by: {decided_by}")
        self.step(f"decision {card}: {chosen}")

        run, written = agents.write_blind_tests(self.f, self.task(), self.name, [
            f"A person decided: {question} Answer: {chosen}. Pin exactly this behavior (it may differ from your earlier assumption)."
        ])
        self.commit("tester", f"Blind tests that pin the decision ({self.slug}, card {card})")
        self.step("tester pins the decision, blind", run, files=written)
        failures, _ = run_suites(self.f, root)
        if failures:
            self.step(f"{len(failures)} tests fail against the decision, the author changes the code", agents.author(self.f, (
                f"A person decided, for the task in `{self.task_path}`: {question} Answer: {chosen}. "
                f"The tester's tests in `{self.f.suites['tester']}/` now pin it and fail. Change the code (and your own "
                f"tests where they assumed otherwise) until `{self.f.test_command}` is green. Never edit the tester's tests."
            )))
            self.commit("author", f"Implement the decision ({self.slug}, card {card})")
        return self.finish(self.close_gaps(dict(record.get("equivalent", {})), max_rounds))

    def plan(self) -> None:
        self.step("plan", agents.author(self.f, (
            f"A person wrote this issue:\n\n{self.issue}\n\n"
            f"Do not implement it yet. Write `{self.task_path}`: the issue in the person's words, then a section "
            "`## Interface` with the exact signatures you will add, then `## Assumptions` for anything the issue "
            "leaves open, with the choice you take, as a list `- A1. ...`, `- A2. ...` (a person sees each as a "
            "card and may change it). Add the new names to `src/` as stubs "
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
                       if self.f.is_source(f) and (self.f.root / f).exists()}
            after = [m for m in mutation.run(self.f, work, targets) if m.id not in res.equivalent]
        finally:
            shutil.rmtree(work, ignore_errors=True)
        dest = f".factory/proposals/{self.slug}/{path}"
        (self.f.root / dest).parent.mkdir(parents=True, exist_ok=True)
        (self.f.root / dest).write_text(text)
        self.commit("tester", f"Proposal for the owners: invariant tests that cover {self.slug}")
        caught = sum(1 for m in after if "invariants" in m.caught_by)
        return {"file": dest, "target": path, "before": res.caught("invariants"), "after": caught, "n": len(after)}
