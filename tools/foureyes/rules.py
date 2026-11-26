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
    invariants = [i for i in factory.invariants if any(matches(path, p) for p in i.paths)]
    if invariants:
        out.append("## Invariants (never broken; the gate blocks)\n")
        out += [f"- **{i.id}** {i.statement} *Why:* {i.why}" for i in invariants]
        out.append("")
    standards = [s for s in factory.standards if any(matches(path, p) for p in s.paths)]
    for s in standards:
        out.append(f"## Standard: {s.file} (how it is done here; the reviewer checks it)\n")
        out.append((factory.root / s.file).read_text().split("\n", 1)[1].strip() + "\n")
    if not invariants and not standards:
        out.append("No invariants or standards apply here beyond the gate.")
    return "\n".join(out)
