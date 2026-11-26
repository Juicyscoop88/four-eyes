"""The tester and the reviewer: headless Claude Code, each in a workspace that holds only what it may see.

Isolation is physical. The tester's workspace has the interface of the code (signatures and
docstrings) but not one line of implementation, and not the author's tests. The reviewer's
workspace is empty: it gets the task, the diff, the invariants and the gate's results in its prompt.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from gate.config import Factory
from gate.tests import checkout_copy

PLUGIN = Path(__file__).resolve().parents[2] / "plugin"


@dataclass
class AgentRun:
    role: str
    model: str
    result: str
    cost_usd: float
    turns: int


def role_prompt(role: str) -> str:
    """The role's instructions, from the plugin's agent file, so local and CI share one text."""
    text = (PLUGIN / "roles" / f"{role}.md").read_text()
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).strip()


def claude(role: str, prompt: str, cwd: Path, model: str, tools: str) -> AgentRun:
    cmd = [
        "claude", "-p", prompt,
        "--append-system-prompt", role_prompt(role),
        "--model", model,
        "--tools", tools,
        "--permission-mode", "acceptEdits",
        "--output-format", "json",
        "--no-session-persistence",
        "--strict-mcp-config",
    ]
    if os.environ.get("ANTHROPIC_API_KEY"):
        cmd.append("--bare")  # CI: no hooks, no plugins, no keychain; only the API key
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        raise RuntimeError(f"{role} agent failed: {out.stderr.strip() or out.stdout.strip()}")
    data = json.loads(out.stdout)
    return AgentRun(role, model, data.get("result", ""), data.get("total_cost_usd", 0.0), data.get("num_turns", 0))


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
    for path in (ws / "src").rglob("*.py"):
        path.write_text(stub_source(path.read_text()))
    author = factory.suites["author"]
    for hidden in (author, "docs", ".claude", ".claude-plugin", "plugin", "tools", ".factory"):
        shutil.rmtree(ws / hidden, ignore_errors=True)
    return ws


def write_blind_tests(factory: Factory, task: str, name: str) -> tuple[AgentRun, list[str]]:
    """The tester writes tests for the task without seeing the code. Returns the files it wrote."""
    ws = tester_workspace(factory)
    folder = factory.suites["tester"]
    target = f"{folder}/test_{name}.py"
    prompt = (
        f"The task:\n\n{task}\n\n"
        f"Write the tests for this task in `{target}`. The implementation is not in this workspace; "
        "the files in `src/` show only the interface. Read them and the invariants, then write the tests."
    )
    run = claude("tester", prompt, ws, factory.model, "Read,Glob,Grep,Write,Edit")
    written = []
    for f in sorted((ws / folder).rglob("*.py")) if (ws / folder).exists() else []:
        rel = f.relative_to(ws).as_posix()
        dest = factory.root / rel
        if not dest.exists() or dest.read_text() != f.read_text():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            written.append(rel)
    shutil.rmtree(ws, ignore_errors=True)
    return run, written


# ---- reviewer -------------------------------------------------------------------------------


@dataclass
class Review:
    run: AgentRun
    map: list[dict]       # [{"where": "src/x.py:12", "why": "..."}], at most three
    findings: list[dict]  # [{"severity": "block|warn", "where": "...", "what": "..."}]
    summary: str


def review(factory: Factory, task: str, diff: str, gate_facts: str) -> Review:
    invariants = "\n".join(f"- {i.id}: {i.statement} ({i.why})" for i in factory.invariants)
    prompt = (
        f"## Task\n\n{task}\n\n## Owned invariants\n\n{invariants}\n\n"
        f"## What the gate measured\n\n{gate_facts}\n\n## The diff\n\n```diff\n{diff}\n```\n"
    )
    ws = Path(tempfile.mkdtemp(prefix="gate-review-"))
    run = claude("reviewer", prompt, ws, factory.model, "")
    shutil.rmtree(ws, ignore_errors=True)
    block = re.search(r"```json\s*(\{.*?\})\s*```", run.result, re.S)
    data = json.loads(block.group(1) if block else run.result)
    return Review(run, data.get("map", [])[:3], data.get("findings", []), data.get("summary", ""))
