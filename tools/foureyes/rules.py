"""What applies to a file: the one answer an agent needs before it changes it."""

from foureyes.config import Factory, matches


def rules_for(factory: Factory, path: str) -> str:
    tier = factory.tier_of(path)
    out = [f"# Rules for `{path}`\n"]
    if factory.is_owned(path):
        out.append("**Owned by people.** An agent never edits this file. Propose a change to its owners instead.\n")
    gate = f"tier **{tier.name}**: independent tests must catch {tier.mutation_min:.0%} of injected faults"
    if tier.approver:
        gate += f", approver from `{tier.approver}`"
    out.append(f"The gate: {gate}. Tests come from the tester, who never sees the code; your own tests do not count.\n")
    named = [r for r in factory.rules if any(matches(path, p) for p in r.paths)]
    if named:
        out.append("## Rules the protected tests hold (the gate blocks when one breaks)\n")
        out += [f"- **{i.id}** {i.statement} *Why:* {i.why}" for i in named]
        out.append("")
    standards = [s for s in factory.standards if any(matches(path, p) for p in s.paths)]
    for s in standards:
        if s.company:
            out.append(f"## Company standard: {s.source.stem} (the same in every FTMO repo; the reviewer checks it. "
                       "A reason to differ goes to its owners as a proposal, never as a change here)\n")
        else:
            out.append(f"## Standard: {s.file} (how it is done in this repo; the reviewer checks it)\n")
        out.append(s.text().split("\n", 1)[1].strip() + "\n")
    protected = factory.suites.get("protected")
    if protected:
        out.append(f"## Protected tests (`{protected}`)\n\nOwned by people: never edit or delete them to make a check "
                   "pass. If one fails, fix the code; if it looks wrong, tell the person.\n")
    if not named and not standards and not protected:
        out.append("No protected tests or standards apply here beyond the gate.")
    return "\n".join(out)
