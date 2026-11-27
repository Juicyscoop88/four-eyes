"""The gate: what a change must prove before it merges.

1. Owned files (protected tests, factory.yaml) need their owners, never an agent.
2. Every suite passes, and a broken invariant is named in words.
3. Mutation: the tester's and the protected tests catch enough faults injected into the changed
   lines. The author's own tests are measured too, but they do not count: nobody checks their own work.
4. The reviewer, who never saw the author's conversation, writes a review map: where a person must look.
"""

import re
import shutil
from dataclasses import dataclass, field

from foureyes import agents, mutation
from foureyes.config import Factory
from foureyes.diff import changed_files, changed_lines, diff_text, git
from foureyes.tests import Failure, base_copy, checkout_copy, run_suites

INDEPENDENT = ("tester", "protected")
SUITE_NAMES = {"tester": "of the tester's tests", "author": "of the author's own tests", "other": "other tests",
               "protected": "of the protected tests (owned by people)"}


@dataclass
class Result:
    base: str
    files: list[str]
    tier: str
    owned_changed: list[str] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    tests_run: int = 0
    mutants: list[mutation.Mutant] = field(default_factory=list)
    mutation_min: float = 0.0
    review: agents.Review | None = None
    agent_runs: list[agents.AgentRun] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    equivalent: dict[str, str] = field(default_factory=dict)  # mutant id -> why no input tells it apart
    proposal: dict | None = None  # an extension of the owned invariant tests, for their owners
    assumptions: list[str] = field(default_factory=list)  # what the plan assumed where the issue was silent
    open: list[Failure] = field(default_factory=list)  # the tester's open questions (test_open_*) the code answers otherwise
    blind_written: list[str] = field(default_factory=list)  # blind tests the gate's tester wrote for a hand-made change
    preexisting: list[Failure] = field(default_factory=list)  # red on the base already: not this change's, never a block

    def cards(self) -> list[dict]:
        """Every decision a person can make on this change, with ids: 1, 2, 3 from the reviewer, A1.. from the plan."""
        out = [{**c, "id": str(i)} for i, c in enumerate(self.review.map if self.review else [], 1)]
        out += [{"id": f"Q{i}", "question": f"The tester asked, the code answers otherwise: {f.test}: {f.message}",
                 "options": ["code: the code is right, the tester's test changes", "test: the test is right, the code changes"]}
                for i, f in enumerate(self.open, 1)]
        out += [{"id": f"A{i}", "question": a, "options": ["keep"]} for i, a in enumerate(self.assumptions, 1)]
        return out

    @property
    def passed(self) -> bool:
        return not self.blocks

    @property
    def counted(self) -> list[mutation.Mutant]:
        return [m for m in self.mutants if m.id not in self.equivalent]

    def caught(self, *suites: str) -> int:
        return sum(1 for m in self.counted if m.caught_by & set(suites))

    @property
    def score(self) -> float:
        return self.caught(*INDEPENDENT) / len(self.counted) if self.counted else 1.0

    @property
    def survivors(self) -> list[mutation.Mutant]:
        return [m for m in self.counted if not m.caught_by & set(INDEPENDENT)]


def strictest(factory: Factory, files: list[str]):
    order = [t.name for t in factory.tiers]
    tiers = [factory.tier_of(f) for f in files] or [factory.tiers[-1]]
    return min(tiers, key=lambda t: order.index(t.name))


def check(
    factory: Factory, base: str, task: str | None, with_agents: bool,
    equivalent: dict[str, str] | None = None, log=print,
) -> Result:
    base = git(factory.root, "rev-parse", base).strip()
    files = changed_files(factory.root, base)
    tier = strictest(factory, files)
    res = Result(base=base, files=files, tier=tier.name, mutation_min=tier.mutation_min)
    res.equivalent = dict(equivalent or {})
    res.assumptions = assumptions_of(task or "")
    log(f"gate: {len(files)} changed files, tier {tier.name}")

    res.owned_changed = [f for f in files if factory.is_owned(f)]
    if tier.mutation_min > 0 and any(factory.is_source(f) for f in files) and not has_spec(task):
        # Independent tests are written from the task alone: a change to risky code without one cannot be checked.
        res.blocks.append(NO_SPEC)
    if res.owned_changed:
        res.blocks.append(f"owned files changed, owner approval required: {', '.join(res.owned_changed)}")

    targets = {
        f: changed_lines(factory.root, base, f)
        for f in files
        if factory.is_source(f) and (factory.root / f).exists()
    }
    work = checkout_copy(factory.root)
    try:
        if with_agents and task and targets and not any(factory.suite_of(f) == "tester" for f in files):
            # Written by hand or by someone's own agent: nobody independent tested it yet. The tester writes blind
            # tests from the pull request's description into the gate's copy; the branch stays as it is.
            log("gate: no blind tests in this change, the tester writes them without seeing the code")
            run, res.blind_written = agents.write_blind_tests(factory, task, "this_change", dest_root=work)
            res.agent_runs.append(run)
        log("gate: running the suites")
        res.failures, res.tests_run = run_suites(factory, work)
        # The tester's own guesses where the task is silent are questions for a person, never a block.
        res.open = [f for f in res.failures if f.suite == "tester" and is_open(f.test)]
        res.failures = [f for f in res.failures if f not in res.open]
        if res.failures:
            log("gate: tests fail, checking which already failed on the base")
            res.preexisting = already_failing(factory, base, res.failures)
            res.failures = [f for f in res.failures if f not in res.preexisting]
        broken = {inv.id: inv for f in res.failures if (inv := rule_of(factory, f))}
        res.blocks += [f"{inv.id} broken: {inv.statement}" for inv in broken.values()]
        for suite in ("tester", "author", "other", "collection", "timeout", "protected"):
            # an invariant test that names its invariant is blocked above, in words; any other one blocks here
            n = sum(1 for f in res.failures if f.suite == suite and not (suite == "protected" and rule_of(factory, f)))
            if n:
                res.blocks.append(f"{n} {SUITE_NAMES.get(suite, suite)} fail")

        if not res.failures and targets and tier.mutation_min > 0:
            log("gate: mutation testing the changed lines")
            res.mutants = mutation.run(factory, work, targets, paths=mutation_tests(factory, files))
            if res.score < tier.mutation_min and not with_agents and not res.caught(*INDEPENDENT):
                # Nothing independent could catch anything: no tester ran. Say why, not just the number.
                res.blocks.append(NO_TESTER)
            elif res.score < tier.mutation_min:
                res.blocks.append(
                    f"independent tests caught {res.caught(*INDEPENDENT)} of {len(res.counted)} injected faults, "
                    f"tier {tier.name} needs {tier.mutation_min:.0%}"
                )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if with_agents:
        log("gate: the reviewer reads the diff")
        res.review = agents.review(factory, task or "(no task given)", diff_text(factory.root, base), facts(res))
        res.agent_runs.append(res.review.run)
        res.blocks += [
            f"reviewer at `{f.get('where', '')}`: {first_sentence(f.get('what', ''))}"
            for f in res.review.findings if f.get("severity") == "block"
        ]
    return res


def already_failing(factory: Factory, base: str, failures: list[Failure]) -> list[Failure]:
    """The failures that the base revision has too. A mature repo often has a red test nobody fixed yet; it is
    reported, but it neither blocks this change nor sends its author to fix someone else's test. An owned invariant
    is the exception: red on the base or not, a broken invariant always blocks."""
    failures = [f for f in failures if f.suite not in ("collection", "timeout", "protected")]
    files = sorted({f.file for f in failures})
    if not files:
        return []
    work = base_copy(factory.root, base)
    try:
        present = tuple(f for f in files if (work / f).is_file())
        if not present:
            return []
        red, _ = run_suites(factory, work, paths=present)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    before = {f.key for f in red}
    return [f for f in failures if f.key in before]


def mutation_tests(factory: Factory, files: list[str]) -> tuple[str, ...]:
    """What runs against each mutant: the tests whose verdict the gate uses. The independent suites count; the
    author's own tests of this change are measured. The rest of the repo's tests cost time and decide nothing."""
    independent = tuple(factory.suites[n] for n in INDEPENDENT if n in factory.suites)
    own = tuple(f for f in files if f.endswith(".py") and factory.suite_of(f) == "author" and (factory.root / f).exists())
    return independent + own


NO_SPEC = ("no task: the change says nowhere what it should do and why. Write it in the pull request description, "
           "with one example and its expected result; the tester writes its tests from it, without seeing the code")


NO_TESTER = ("no independent tests yet: the tester writes them, and in CI it needs the repo's ANTHROPIC_API_KEY. "
             "An admin adds it once, best for the whole organisation; then this check runs again")


def has_spec(task: str | None) -> bool:
    """Enough of a task to test against: a few sentences, not an empty or one-word description."""
    return bool(task) and len(" ".join(task.split())) >= 40


def is_open(test: str) -> bool:
    return test.split("[")[0].rsplit("::", 1)[-1].startswith("test_open_")


def assumptions_of(task: str) -> list[str]:
    """The numbered items of the task's `## Assumptions` section, one string each."""
    if "## Assumptions" not in task:
        return []
    section = task.split("## Assumptions", 1)[1].split("\n## ", 1)[0]
    items: list[str] = []
    for line in section.splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?A?\d+[.)]\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
        elif items and line.strip():
            items[-1] += " " + line.strip()
    return items


def first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text, re.S)
    return m.group(1) if m else text


def rule_of(factory: Factory, failure: Failure):
    if failure.suite != "protected":
        return None
    m = re.match(r"(?:AssertionError: )?([A-Z]+-\d+):", failure.message)
    return factory.rule(m.group(1)) if m else None


def facts(res: Result) -> str:
    lines = [f"Tier: {res.tier}. Tests run: {res.tests_run}, failed: {len(res.failures)}."]
    lines += [f"- failed {f.suite}: {f.test}: {f.message}" for f in res.failures]
    lines += [f"- already failing on the base, not caused by this change: {f.test}: {f.message}" for f in res.preexisting]
    if res.mutants:
        lines.append(f"Mutation: {len(res.counted)} faults injected into the changed lines.")
        for suite in ("author", "tester", "protected"):
            lines.append(f"- {suite} tests caught {res.caught(suite)}")
        lines += [f"- {m.id} survived the independent tests: {m.path}:{m.line} {m.description}" for m in res.survivors]
        lines += [f"- {i} judged equivalent: {why}" for i, why in res.equivalent.items()]
    return "\n".join(lines)

