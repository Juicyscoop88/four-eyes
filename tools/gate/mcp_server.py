"""FourEyes MCP: the factory's live facts for people and agents in Claude Code.

The gate's verdict is never decided here: that is deterministic code (`gate check` in CI). These tools
advise and explain. Roles get different tools: the tester gets only rules_for, because why and check
would show it the code it must not see.
"""

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from gate.check import check as run_check, facts
from gate.config import load
from gate.diff import git
from gate.rules import rules_for as _rules_for
from gate.why import why as _why

server = MCPServer(
    "foureyes",
    instructions=(
        "FourEyes is this repository's software factory: nobody, human or agent, checks their own work. "
        "Call rules_for before you change a file. Call why when someone asks why code is the way it is, "
        "who asked for it or who decided. Call check before you say a change is done."
    ),
)


def _factory():
    return load(Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip()))


@server.tool()
def rules_for(path: str) -> str:
    """Call this BEFORE you create or change a file. Returns what applies to that path in this repository:
    whether people own it (then you must not edit it), its risk tier and what the gate will demand, the owned
    invariants that must never break there, and the standards for how things are done there (for example the
    design system for apps). path is relative to the repository root."""
    return _rules_for(_factory(), path)


@server.tool()
def why(path: str, line: int) -> str:
    """Call this when someone asks why a line of code exists or is the way it is, who asked for it, who
    decided, or what protects it: for an audit, a review, or before changing behavior you did not write.
    Returns the commit and its role (author agent, tester agent, person), who asked, the task, the decisions
    people made on it, the tests that fail when the line is broken, and the pull request with its approvals."""
    return _why(_factory(), path, line)


@server.tool()
def check(base: str = "main") -> str:
    """Call this before you say a change is done. Runs the gate's tests and mutation testing on the changes
    since base, without agents, and returns only what matters: passed or what blocks, and which injected
    faults no independent test caught. The binding verdict is the same check in CI."""
    factory = _factory()
    res = run_check(factory, base, None, False, log=lambda m: None)
    head = "Passed." if res.passed else "Blocked:\n" + "\n".join(f"- {b}" for b in res.blocks)
    return f"{head}\n\n{facts(res)}"


def main() -> None:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    server.run("stdio")
