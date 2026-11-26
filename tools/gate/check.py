"""The gate: what a change must prove before it merges.

1. Owned files (invariants, their tests, factory.yaml) need their owners, never an agent.
2. Every suite passes, and a broken invariant is named in words.
3. Mutation: the tester's and the invariants' tests catch enough faults injected into the changed
   lines. The author's own tests are measured too, but they do not count: nobody checks their own work.
4. The reviewer, who never saw the author's conversation, writes a review map: where a person must look.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from gate import agents, mutation
from gate.config import Factory
from gate.diff import changed_files, changed_lines, diff_text, git
from gate.tests import Failure, checkout_copy, run_suites

INDEPENDENT = ("tester", "invariants")
SUITE_NAMES = {"tester": "of the tester's tests", "author": "of the author's own tests", "other": "other tests"}


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
    log(f"gate: {len(files)} changed files, tier {tier.name}")

    res.owned_changed = [f for f in files if factory.is_owned(f)]
    if res.owned_changed:
        res.blocks.append(f"owned files changed, owner approval required: {', '.join(res.owned_changed)}")

    work = checkout_copy(factory.root)
    try:
        log("gate: running the suites")
        res.failures, res.tests_run = run_suites(factory, work)
        broken = {inv.id: inv for f in res.failures if (inv := invariant_of(factory, f))}
        res.blocks += [f"{inv.id} broken: {inv.statement}" for inv in broken.values()]
        for suite in ("tester", "author", "other", "collection", "timeout"):
            n = sum(1 for f in res.failures if f.suite == suite)
            if n:
                res.blocks.append(f"{n} {SUITE_NAMES.get(suite, suite)} fail")

        targets = {
            f: changed_lines(factory.root, base, f)
            for f in files
            if f.startswith("src/") and f.endswith(".py") and (factory.root / f).exists()
        }
        if not res.failures and targets and tier.mutation_min > 0:
            log("gate: mutation testing the changed lines")
            res.mutants = mutation.run(factory, work, targets)
            if res.score < tier.mutation_min:
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


def first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text, re.S)
    return m.group(1) if m else text


def invariant_of(factory: Factory, failure: Failure):
    if failure.suite != "invariants":
        return None
    m = re.match(r"(?:AssertionError: )?([A-Z]+-\d+):", failure.message)
    return factory.invariant(m.group(1)) if m else None


def facts(res: Result) -> str:
    lines = [f"Tier: {res.tier}. Tests run: {res.tests_run}, failed: {len(res.failures)}."]
    lines += [f"- failed {f.suite}: {f.test}: {f.message}" for f in res.failures]
    if res.mutants:
        lines.append(f"Mutation: {len(res.counted)} faults injected into the changed lines.")
        for suite in ("author", "tester", "invariants"):
            lines.append(f"- {suite} tests caught {res.caught(suite)}")
        lines += [f"- {m.id} survived the independent tests: {m.path}:{m.line} {m.description}" for m in res.survivors]
        lines += [f"- {i} judged equivalent: {why}" for i, why in res.equivalent.items()]
    return "\n".join(lines)


# ---- report: the merge request comment ------------------------------------------------------


def report(factory: Factory, res: Result, head: str) -> str:
    verdict = "✅ **Passed.** A person approves the merge." if res.passed else "⛔ **Blocked.**"
    out = [f"## Four Eyes gate\n\n{verdict} Tier **{res.tier}**.\n"]
    if res.blocks:
        out += ["### What blocks it\n"] + [f"- {b}" for b in res.blocks] + [""]

    if res.review and res.review.map:
        out.append("### Review map: decide only these\n")
        for i, p in enumerate(res.review.map, 1):
            out.append(f"**{i}. {p.get('question') or p['why']}**  \n`{p['where']}`: {p['why']}")
            if p.get("options"):
                out.append("Answer with one: " + " · ".join(f"`{o}`" for o in p["options"]))
            out.append("")
    if res.review and res.review.summary:
        out += [f"> {res.review.summary}\n"]

    out.append(f"### Tests\n\n{res.tests_run} tests ran, {len(res.failures)} failed.\n")
    for f in res.failures:
        inv = invariant_of(factory, f)
        label = f"**{inv.id}** {inv.statement} *Why it matters:* {inv.why}" if inv else f"`{f.test}`"
        out.append(f"- {f.suite}: {label}\n  `{f.message}`")
    if res.failures:
        out.append("")

    if res.mutants:
        n = len(res.counted)
        out.append("### Do the tests prove anything?\n")
        eq = f" ({len(res.equivalent)} more changed no behavior, see below)" if res.equivalent else ""
        out.append(f"{n} small faults were injected into the changed lines, one at a time{eq}.\n")
        out.append("| Tests | Written by | Caught | Counts |\n|---|---|---|---|")
        out.append(f"| author | whoever wrote the code | {res.caught('author')} of {n} | no, nobody checks their own work |")
        out.append(f"| tester | the tester, who never saw the code | {res.caught('tester')} of {n} | yes |")
        out.append(f"| invariants | people (owned) | {res.caught('invariants')} of {n} | yes |")
        out.append(f"| **tester + invariants** | | **{res.caught(*INDEPENDENT)} of {n}** ({res.score:.0%}, needs {res.mutation_min:.0%}) | |\n")
        if res.survivors:
            out.append("<details><summary>Faults no independent test caught</summary>\n")
            out += [f"- {m.id} `{m.path}:{m.line}` {m.description}" for m in res.survivors]
            out.append("\n</details>\n")
        if res.equivalent:
            out.append("<details><summary>Faults judged equivalent by the reviewer (not counted)</summary>\n")
            out += [f"- {i} `{m.path}:{m.line}` {m.description}: {res.equivalent[i]}"
                    for m in res.mutants if (i := m.id) in res.equivalent]
            out.append("\n</details>\n")

    if res.proposal:
        p = res.proposal
        out.append("### For the owners of the invariants\n")
        out.append(
            f"The owned invariant tests caught {p['before']} of {p['n']} faults in this change: they do not "
            f"exercise it yet. The tester (blind) proposes an extension in `{p['file']}`. With it, the "
            f"invariants catch **{p['after']} of {p['n']}**, and it passes on the current code. "
            "Only an owner can accept it.\n"
        )

    if res.review and res.review.findings:
        out.append("### Reviewer findings\n")
        out += [f"- **{f.get('severity', 'warn')}** `{f.get('where', '')}`: {f.get('what', '')}" for f in res.review.findings]
        out.append("")

    roles = ", ".join(f"{r.role} ({r.model}, ${r.cost_usd:.3f})" for r in res.agent_runs) or "none"
    cost = sum(r.cost_usd for r in res.agent_runs)
    out.append("### Provenance\n")
    out.append(f"- change: `{res.base[:10]}..{head[:10]}`, {len(res.files)} files")
    out.append(f"- requested by: {author_of(factory.root)}; approver must be someone else")
    out.append(f"- agents that checked it: {roles}; total ${cost:.3f}")
    if res.owned_changed:
        out.append(f"- owned files touched: {', '.join(res.owned_changed)}")
    out.append(f"- gate run: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    return "\n".join(out) + "\n"


def author_of(root: Path) -> str:
    try:
        return git(root, "config", "user.name").strip() or "unknown"
    except subprocess.CalledProcessError:
        return "unknown"
