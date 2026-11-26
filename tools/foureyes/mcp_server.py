"""FourEyes MCP: the factory's live facts for people and agents in Claude Code.

The gate's verdict is never decided here: that is deterministic code (`foureyes check` in CI). These tools
advise and explain. Only the author's session gets them: why would show the tester the code it must
not see, and the reviewer judges the diff on its own.
"""

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from foureyes.config import load
from foureyes.diff import git
from foureyes.rules import rules_for as _rules_for
from foureyes.why import why as _why

server = MCPServer(
    "foureyes",
    instructions=(
        "FourEyes is this repository's software factory: nobody, human or agent, checks their own work. "
        "Call rules_for before you change a file. Call why when someone asks why code is the way it is, "
        "who asked for it or who decided. The gate in CI gives the verdict; these tools only advise and explain."
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



def main() -> None:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    server.run("stdio")
