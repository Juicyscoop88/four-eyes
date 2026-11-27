"""The roles: headless Claude Code, each in a workspace that holds only what it may see.

Isolation is physical. The tester's workspace has the interface of the code (signatures and
docstrings) but not one line of implementation, and not the author's tests. The reviewer's
workspace is empty: it gets the task, the diff, the invariants and the gate's results in its prompt.
The author works in the repo itself, under the plugin's hooks, like an engineer's own Claude Code.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from foureyes.config import Factory
from foureyes.tests import checkout_copy

PLUGIN = Path(__file__).resolve().parents[2] / "plugin"


@dataclass
class AgentRun:
    role: str
    model: str
    result: str
    cost_usd: float
    turns: int
    seconds: float = 0.0


def role_prompt(role: str) -> str:
    """The role's instructions, from the plugin's role file, so local and CI share one text."""
    text = (PLUGIN / "roles" / f"{role}.md").read_text()
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).strip()


def claude(
    role: str, prompt: str, cwd: Path, factory: Factory, tools: str,
    allowed: tuple[str, ...] = (), hooks: bool = False, timeout: int = 900, model: str = "",
) -> AgentRun:
    """One headless agent, hermetic: its MCP servers come from factory.yaml only, and no user
    settings (plugins, hooks, permissions) of the machine it runs on. Same tools on every laptop and in CI."""
    model = model or factory.models.get(role, factory.models["reviewer"])
    servers = factory.mcp.get(role, ())
    cmd = [
        "claude", "-p", prompt,
        "--append-system-prompt", role_prompt(role),
        "--model", model,
        "--tools", tools,
        "--permission-mode", "acceptEdits",
        "--output-format", "json",
        "--no-session-persistence",
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--mcp-config", json.dumps({"mcpServers": {n: factory.servers[n] for n in servers}}),
    ]
    allowed = (*allowed, *(f"mcp__{n}" for n in servers))
    if hooks:
        cmd += ["--plugin-dir", str(PLUGIN)]  # the author works under the plugin's hooks
    if allowed:
        cmd += ["--allowedTools", *allowed]
    if not hooks and os.environ.get("ANTHROPIC_API_KEY"):
        cmd.append("--bare")  # CI checkers: no hooks, no plugins, no keychain; only the API key
    started = time.monotonic()
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(f"{role} agent failed: {out.stderr.strip() or out.stdout.strip()}")
    data = json.loads(out.stdout)
    return AgentRun(
        role, model, data.get("result", ""), data.get("total_cost_usd", 0.0), data.get("num_turns", 0),
        round(time.monotonic() - started, 1),
    )


def json_block(text: str) -> dict:
    block = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    return json.loads(block.group(1) if block else text)


# ---- author ---------------------------------------------------------------------------------


def author(factory: Factory, prompt: str) -> AgentRun:
    """The author in the repo itself, under the plugin's hooks. It may run the tests, nothing else."""
    return claude(
        "author", prompt, factory.root, factory, "Read,Glob,Grep,Write,Edit,Bash",
        allowed=(f"Bash({factory.test_command}:*)",), hooks=True, timeout=1500,
    )


# ---- tester ---------------------------------------------------------------------------------


def stub_source(source: str) -> str:
    """Keep classes, signatures, docstrings and constants; replace every function body."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            body: list[ast.stmt] = [ast.Expr(ast.Constant(doc))] if doc else []
            body.append(ast.Raise(ast.Call(ast.Name("NotImplementedError"), [], [])))
            node.body = body
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def tester_workspace(factory: Factory) -> Path:
    ws = checkout_copy(factory.root)
    for path in (ws / factory.source).rglob("*.py"):
        path.write_text(stub_source(path.read_text()))
    author_tests = factory.suites["author"]
    for hidden in (author_tests, "docs", ".claude", ".claude-plugin", "plugin", "tools", ".factory"):
        shutil.rmtree(ws / hidden, ignore_errors=True)
    return ws


def copy_back(ws: Path, root: Path, folder: str, dest_folder: str | None = None) -> list[str]:
    """Files the tester wrote or changed in folder, copied into the repo. Returns their repo paths."""
    written = []
    src_dir = ws / folder
    for f in sorted(src_dir.rglob("*.py")) if src_dir.exists() else []:
        rel = (Path(dest_folder or folder) / f.relative_to(src_dir)).as_posix()
        dest = root / rel
        if not dest.exists() or dest.read_text() != f.read_text():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            written.append(rel)
    return written


def write_blind_tests(
    factory: Factory, task: str, name: str, gaps: list[str] = (),
    model: str | None = None, dest_root: Path | None = None, fresh: bool = False,
) -> tuple[AgentRun, list[str]]:
    """The tester writes tests for the task without seeing the code. Returns the files it wrote.

    gaps: behaviors no independent test checks yet, in words (from the reviewer, never code).
    model, dest_root, fresh: for the eval, another tester model writing from scratch into a copy."""
    ws = tester_workspace(factory)
    folder = factory.suites["tester"]
    target = f"{folder}/test_{name}.py"
    if fresh:
        (ws / target).unlink(missing_ok=True)
    prompt = f"The task:\n\n{task}\n\n"
    if gaps:
        prompt += (
            f"Your tests in `{target}` already exist. The gate found behaviors they do not pin down yet. "
            "Add tests for each, keep the existing ones:\n\n" + "\n".join(f"- {g}" for g in gaps) + "\n\n"
        )
    else:
        prompt += f"Write the tests for this task in `{target}`. "
    prompt += (
        "The implementation is not in this workspace; the files in `src/` show only the interface. "
        "Read them and the invariants, then write the tests."
    )
    run = claude("tester", prompt, ws, factory, "Read,Glob,Grep,Write,Edit", model=model)
    written = copy_back(ws, dest_root or factory.root, folder)
    shutil.rmtree(ws, ignore_errors=True)
    return run, written


def propose_invariant_tests(factory: Factory, task: str, name: str) -> tuple[AgentRun, dict[str, str]]:
    """The owned property tests do not exercise the new interface. The tester (blind) proposes an
    extension for their owners. It never touches the owned files: it writes proposals beside them.
    Returns {owned test path: proposed text}."""
    ws = tester_workspace(factory)
    owned_tests = sorted({i.test.split("::")[0] for i in factory.invariants})
    prompt = (
        f"The task that was just implemented:\n\n{task}\n\n"
        f"The owned property tests ({', '.join(owned_tests)}) do not exercise what this task adds, so the "
        "invariants do not protect it yet. Propose an extension for their owners: write a full copy of "
        "each file you would change under `proposal/`, at the same path (for example "
        f"`proposal/{owned_tests[0]}`). Keep every existing invariant check exactly as it is; add the new "
        "operation to the random steps so that every invariant is checked after it too. Keep the "
        "invariant ids in the assertion messages. Change nothing else."
    )
    run = claude("tester", prompt, ws, factory, "Read,Glob,Grep,Write,Edit")
    proposals = {}
    for path in owned_tests:
        f = ws / "proposal" / path
        if f.exists():
            proposals[path] = f.read_text()
    shutil.rmtree(ws, ignore_errors=True)
    return run, proposals


# ---- reviewer -------------------------------------------------------------------------------


@dataclass
class Review:
    run: AgentRun
    map: list[dict]       # [{"where", "why", "question", "options"}], at most three: the decision cards
    findings: list[dict]  # [{"severity": "block|warn", "where": "...", "what": "..."}]
    summary: str
    gaps: list[dict] = field(default_factory=list)


def _invariants(factory: Factory) -> str:
    return "\n".join(f"- {i.id}: {i.statement} ({i.why})" for i in factory.invariants)


def review(factory: Factory, task: str, diff: str, gate_facts: str) -> Review:
    prompt = (
        f"## Task\n\n{task}\n\n## Owned invariants\n\n{_invariants(factory)}\n\n"
        f"## What the gate measured\n\n{gate_facts}\n\n## The diff\n\n```diff\n{diff}\n```\n"
    )
    ws = Path(tempfile.mkdtemp(prefix="gate-review-"))
    run = claude("reviewer", prompt, ws, factory, "")
    shutil.rmtree(ws, ignore_errors=True)
    data = json_block(run.result)
    return Review(run, data.get("map", [])[:3], data.get("findings", []), data.get("summary", ""))


def explain_gaps(factory: Factory, task: str, diff: str, survivors: list[str]) -> Review:
    """Faults no independent test caught, translated by the reviewer into behaviors in words, so the
    tester can test them without seeing the code. A fault that changes no behavior is marked equivalent."""
    prompt = (
        f"## Task\n\n{task}\n\n## Owned invariants\n\n{_invariants(factory)}\n\n"
        f"## The diff\n\n```diff\n{diff}\n```\n\n"
        "## Faults no independent test caught\n\n" + "\n".join(f"- {s}" for s in survivors) + "\n\n"
        "This time you do not write a review. For each fault, either describe the behavior a test must pin "
        "down so that this fault would fail it, in the words of the task (inputs and expected outcome, never "
        "code, variable names or line numbers: the tester must not learn the implementation), or mark it "
        "equivalent if no input can tell the faulty code from the real one, and say why. Answer with one "
        'JSON block: {"gaps": [{"id": "M3", "equivalent": false, "behavior": "..."}, '
        '{"id": "M5", "equivalent": true, "why": "..."}]}'
    )
    ws = Path(tempfile.mkdtemp(prefix="gate-gaps-"))
    run = claude("reviewer", prompt, ws, factory, "")
    shutil.rmtree(ws, ignore_errors=True)
    data = json_block(run.result)
    return Review(run, [], [], "", data.get("gaps", []))


# ---- adversary (the eval only) --------------------------------------------------------------


def seed_bugs(factory: Factory, task: str, files: dict[str, str], k: int) -> tuple[AgentRun, list[dict]]:
    """An adversary who sees the finished code plants realistic bugs, to measure the factory."""
    shown = "\n\n".join(f"### {p}\n\n```python\n{t}\n```" for p, t in files.items())
    prompt = (
        f"## Task\n\n{task}\n\n## Owned invariants\n\n{_invariants(factory)}\n\n## The code\n\n{shown}\n\n"
        f"Plant {k} different bugs in the code that implements this task. Each is one small edit, the kind a "
        "rushed engineer or agent really makes: a wrong boundary, a forgotten case, a wrong rounding, state "
        "changed before a check, a check in the wrong place. Not syntax errors, not obvious sabotage, and the "
        "code must still import. Answer with one JSON block: "
        '{"bugs": [{"file": "src/...", "find": "exact text that occurs once", "replace": "...", '
        '"why": "what goes wrong, for which input"}]}'
    )
    ws = Path(tempfile.mkdtemp(prefix="gate-adversary-"))
    run = claude("adversary", prompt, ws, factory, "", model=factory.models["reviewer"])
    shutil.rmtree(ws, ignore_errors=True)
    return run, json_block(run.result).get("bugs", [])
