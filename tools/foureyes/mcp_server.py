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
    "four-eyes",
    instructions=(
        "This repository runs the Four Eyes software factory: nobody, human or agent, checks their own work. "
        "Call rules_for before you change a file. Call why when someone asks why code is the way it is, "
        "who asked for it or who decided. Call "
        "propose_standard when people agree on how something should be done here from now on. "
        "The gate in CI gives the verdict; these tools only advise and explain."
    ),
)


NOT_SET_UP = ("This repository is not on Four Eyes yet (no factory.yaml). `/four-eyes:setup` puts it on the "
              "factory: the repo's lead runs it once and reviews the pull request it makes.")


def _root() -> Path:
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())


def _factory():
    root = _root()
    if not (root / "factory.yaml").exists():
        raise ValueError(NOT_SET_UP)
    return load(root)


@server.tool()
def rules_for(path: str) -> str:
    """Call this BEFORE you create or change a file. Returns what applies to that path in this repository:
    whether people own it (then you must not edit it), its risk tier and what the gate will demand, the owned
    the protected tests that hold there, and the standards for how things are done there (for example the
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
def propose_standard(name: str, paths: list[str], text: str) -> str:
    """Call this when people agree on how something should be done in this repo from now on (for example "amounts
    are always rounded half-even", "every screen has a loading state"). Writes the standard as
    standards/<name>.md; from then on everyone who touches those paths gets it. name: short, kebab-case.
    paths: glob patterns it applies to, like ["src/payments/**"]. text: the standard as a few bullet points."""
    f = _factory()
    file = f"standards/{name}.md"
    target = f.root / file
    if target.exists():
        return f"`{file}` exists already. Change it there; a person reviews it in the pull request."
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# {name.replace('-', ' ').capitalize()}\n\n{text.strip()}\n")
    entry = f'  - paths: {paths}\n    file: {file}'.replace("'", '"')
    return (f"Wrote `{file}`. It applies once an owner of `factory.yaml` adds it under `standards:` in the same "
            f"pull request:\n\n```yaml\n{entry}\n```\n\nAn agent never edits factory.yaml: show this to the "
            "person, who adds it and opens the pull request. The owners approve it like any other change.")


def main() -> None:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    server.run("stdio")
