"""The team's week in numbers, from the gate reports that already exist on the pull requests.

It answers the team lead's question ("are we faster, are we safer?") per repo and team, never per person:
how many changes went through the gate, how many it stopped, how much the independent tests caught, what the
agents cost, and how long a change took from pull request to merge.
"""

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from statistics import median

STATS = re.compile(r"<!-- four-eyes-stats (\{.*?\}) -->", re.S)


def stats_of(comments: list[dict]) -> dict | None:
    """The last gate report's numbers among a pull request's comments (the gate edits its comment in place)."""
    found = [STATS.search(c.get("body", "")) for c in comments]
    found = [m for m in found if m]
    return json.loads(found[-1].group(1)) if found else None


def hours(start: str, end: str | None) -> float | None:
    if not end:
        return None
    parse = lambda t: datetime.fromisoformat(t.replace("Z", "+00:00"))  # noqa: E731
    return (parse(end) - parse(start)).total_seconds() / 3600


def summarize(prs: list[dict], days: int) -> str:
    gated = [(pr, s) for pr in prs if (s := stats_of(pr.get("comments", [])))]
    merged = [pr for pr in prs if pr.get("mergedAt")]
    lead = [h for pr in merged if (h := hours(pr["createdAt"], pr["mergedAt"])) is not None]
    mutants = sum(s["mutants"] for _, s in gated)
    caught = sum(s["caught"] for _, s in gated)
    stopped = [s for _, s in gated if not s["passed"]]
    cost = sum(s["cost_usd"] for _, s in gated)
    lines = [
        f"## Four Eyes, the last {days} days",
        "",
        f"- **{len(prs)}** pull requests, **{len(merged)}** merged"
        + (f", median **{median(lead):.1f} h** from opened to merged" if lead else ""),
        f"- **{len(gated)}** went through the gate; it stopped **{len(stopped)}** at least once",
        f"- independent tests caught **{caught} of {mutants}** injected faults"
        + (f" ({caught / mutants:.0%})" if mutants else ""),
        f"- **{sum(s['cards'] for _, s in gated)}** decisions asked of people, "
        f"**{sum(1 for _, s in gated if s['blind_written'])}** hand-made changes got blind tests at the gate",
        f"- agents cost **${cost:.2f}** in all" + (f", **${cost / len(gated):.2f}** per change" if gated else ""),
        "",
        "Per repo and team, never per person: the numbers say how far the tests can be trusted and what the "
        "factory costs, not who is fast.",
    ]
    return "\n".join(lines) + "\n"


def fetch(days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["gh", "pr", "list", "--state", "all", "--limit", "200", "--search", f"updated:>={since}",
         "--json", "number,createdAt,mergedAt,comments"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout or "[]")
