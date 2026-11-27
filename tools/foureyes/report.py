"""The gate's report: the pull request comment a person reads, and the data it carries.

The verdict, the decision cards, the tests, what the injected faults show, the reviewer's findings and who asked.
The cards and the numbers travel in the comment as data, so `/decide` answers exactly the card the person saw and
`foureyes summary` counts the week without parsing prose.
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from foureyes.check import INDEPENDENT, Result, rule_of
from foureyes.config import Factory
from foureyes.diff import git


def report(factory: Factory, res: Result, head: str) -> str:
    verdict = "✅ **Passed.** A person approves the merge." if res.passed else "⛔ **Blocked.**"
    out = [f"## Four Eyes gate\n\n{verdict} Tier **{res.tier}**.\n"]
    if res.blocks:
        out += ["### What blocks it\n"] + [f"- {b}" for b in res.blocks] + [""]

    if res.review and res.review.map:
        out.append("### Decide only these\n")
        out.append("Answer each in one sentence in the pull request description, the spec (in Claude Code just say it): "
                   "the gate runs again and the tester checks your answer. On a pull request the autopilot made, "
                   "reply `/decide 1 keep` instead and it changes the code itself.\n")
        for i, p in enumerate(res.review.map, 1):
            out.append(f"**{i}. {p.get('question') or p['why']}**  \n`{p['where']}`: {p['why']}")
            for o in p.get("options", []):
                key = o.split(":")[0].strip()
                out.append(f"- **{key}**: {o.split(':', 1)[1].strip() if ':' in o else o}")
            out.append("")
    if res.open:
        out.append("### The tester asked\n")
        out.append("Where the issue is silent the tester guessed, and the code chose otherwise. Neither blocks; "
                   "say which is right, for example `/decide Q1 code`.\n")
        for i, f in enumerate(res.open, 1):
            out.append(f"- **Q{i}** `{f.test}`: {f.message}")
        out.append("")
    if res.review and res.review.summary:
        out += [f"> {res.review.summary}\n"]

    if res.assumptions:
        out.append(f"<details><summary>The plan made {len(res.assumptions)} assumptions where the issue was silent. "
                   "Change any with <code>/decide A3 what it should be</code></summary>\n")
        out += [f"- **A{i}** {a}" for i, a in enumerate(res.assumptions, 1)]
        out.append("\n</details>\n")

    out.append(f"### Tests\n\n{res.tests_run} tests ran, {len(res.failures)} failed.\n")
    if res.blind_written:
        out.append("This change came without blind tests, so the gate's tester wrote them from the description, "
                   f"without seeing the code: {', '.join(f'`{w}`' for w in res.blind_written)}. They ran in the gate's "
                   "copy only; the branch is unchanged.\n")
    for f in res.failures:
        inv = rule_of(factory, f)
        label = f"**{inv.id}** {inv.statement} *Why it matters:* {inv.why}" if inv else f"`{f.test}`"
        out.append(f"- {f.suite}: {label}\n  `{f.message}`")
    if res.failures:
        out.append("")
    if res.preexisting:
        out.append(f"{len(res.preexisting)} more already failed on the base branch. They are not this change's and do "
                   "not block it; they are the repo's to fix:\n")
        out += [f"- `{f.test}` (`{f.file}`): `{f.message}`" for f in res.preexisting]
        out.append("")

    if res.mutants:
        n = len(res.counted)
        out.append("### Do the tests prove anything?\n")
        eq = f" ({len(res.equivalent)} more changed no behavior, see below)" if res.equivalent else ""
        out.append(f"{n} small faults were injected into the changed lines, one at a time{eq}.\n")
        out.append("| Tests | Written by | Caught | Counts |\n|---|---|---|---|")
        out.append(f"| author | whoever wrote the code | {res.caught('author')} of {n} | no, nobody checks their own work |")
        out.append(f"| tester | the tester, who never saw the code | {res.caught('tester')} of {n} | yes |")
        out.append(f"| protected | people own them | {res.caught('protected')} of {n} | yes |")
        out.append(f"| **tester + protected** | | **{res.caught(*INDEPENDENT)} of {n}** ({res.score:.0%}, needs {res.mutation_min:.0%}) | |\n")
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
        out.append("### For the owners of the protected tests\n")
        out.append(
            f"The protected tests caught {p['before']} of {p['n']} faults in this change: they do not "
            f"exercise it yet. The tester (blind) proposes an extension in `{p['file']}`. With it, the "
            f"protected tests catch **{p['after']} of {p['n']}**, and it passes on the current code. "
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
    if not res.review:
        out.append("- the reviewer did not run on this change, so there is no review map")
    if res.owned_changed:
        out.append(f"- owned files touched: {', '.join(res.owned_changed)}")
    out.append(f"- gate run: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    # The numbers as data, for the team's summary (`foureyes summary`): per change, never per person.
    stats = {"passed": res.passed, "tier": res.tier, "files": len(res.files), "tests_run": res.tests_run,
             "failures": len(res.failures), "preexisting": len(res.preexisting), "mutants": len(res.counted),
             "caught": res.caught(*INDEPENDENT), "cards": len(res.cards()), "blind_written": bool(res.blind_written),
             "cost_usd": round(cost, 4)}
    out.append(f"\n<!-- four-eyes-stats {json.dumps(stats)} -->")
    if res.cards():
        # The cards as data, so an answer (`/decide 1 keep`) refers to exactly the card the person saw.
        out.append(f"\n<!-- four-eyes-cards {json.dumps(res.cards())} -->")
    return "\n".join(out) + "\n"


def cards_from(comment: str) -> list[dict]:
    m = re.search(r"<!-- four-eyes-cards (.*?) -->", comment, re.S)
    return json.loads(m.group(1)) if m else []


def author_of(root: Path) -> str:
    """Who asked for the change: in CI the pull request's author, locally the git user."""
    if os.environ.get("FACTORY_REQUESTED_BY"):
        return os.environ["FACTORY_REQUESTED_BY"]
    try:
        return git(root, "config", "user.name").strip() or "unknown"
    except subprocess.CalledProcessError:
        return "unknown"
