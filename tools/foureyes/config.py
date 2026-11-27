"""factory.yaml: the one file per repo the gate reads."""

import shutil
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Tier:
    name: str
    paths: list[str]
    mutation_min: float
    approver: str | None


@dataclass(frozen=True)
class Rule:
    id: str
    statement: str
    why: str
    test: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Standard:
    """How things are done. A company standard ships with the factory (one version for every repo); a repo
    standard is a file in the repo, for what only this repo does."""
    paths: tuple[str, ...]
    file: str          # what people see: `standards/x.md`, or `company: x` for a company standard
    source: Path

    @property
    def company(self) -> bool:
        return self.file.startswith("company:")

    def text(self) -> str:
        return self.source.read_text()


@dataclass(frozen=True)
class Factory:
    root: Path
    owned: list[str]
    suites: dict[str, str]
    tiers: list[Tier]
    rules: list[Rule]
    models: dict[str, str]  # role -> model; the tester differs from the author on purpose
    mcp: dict[str, tuple[str, ...]]  # role -> the MCP servers it gets; nothing else from the machine it runs on
    servers: dict[str, dict]         # name -> MCP server definition (the shape of .mcp.json)
    standards: list[Standard]
    source: str = "src"                 # the code the factory protects (stubbed for the tester, mutated by the gate)
    test_command: str = "uv run pytest" # what the author runs
    python: str = ""                    # the interpreter for the suites (see `project_python`)

    def is_source(self, path: str) -> bool:
        return path.startswith(self.source.rstrip("/") + "/") and path.endswith(".py")

    def is_owned(self, path: str) -> bool:
        return any(matches(path, p) for p in self.owned)

    def tier_of(self, path: str) -> Tier:
        for tier in self.tiers:
            if any(matches(path, p) for p in tier.paths):
                return tier
        return self.tiers[-1]

    def suite_of(self, test_path: str) -> str | None:
        """The suite a test file belongs to; the most specific folder wins (tests/blind before tests)."""
        hits = [(len(f), n) for n, f in self.suites.items()
                if test_path == f or test_path.startswith(f.rstrip("/") + "/")]
        return max(hits)[1] if hits else None

    def rule(self, rule_id: str) -> Rule | None:
        return next((r for r in self.rules if r.id == rule_id), None)


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch(path, pattern)


def load(root: Path) -> Factory:
    raw = yaml.safe_load((root / "factory.yaml").read_text())
    tiers = [
        Tier(name, t["paths"], float(t.get("mutation_min", 0)), t.get("approver"))
        for name, t in raw["tiers"].items()
    ]
    rules = []
    for file in raw.get("rules", raw.get("invariants", [])):  # `invariants:` is the first versions' name
        doc = yaml.safe_load((root / file).read_text())
        paths = tuple(doc.get("paths", []))
        rules += [Rule(i["id"], i["statement"], i["why"], i["test"], paths) for i in doc.get("rules", doc.get("invariants", []))]
    return Factory(
        root=root,
        owned=raw.get("owned", []),
        suites=suites(raw["suites"]),
        tiers=tiers,
        rules=rules,
        standards=[standard(root, x) for x in raw.get("standards", [])],
        source=raw.get("source", "src"),
        test_command=raw.get("test_command", "uv run pytest"),
        python=str((root / raw["python"]).absolute()) if raw.get("python") else project_python(root),
        **agents(raw),
    )


def project_python(root: Path) -> str:
    """The project's interpreter when factory.yaml names none: the repo's own .venv if there is one, else the
    `python` on PATH (in CI the runner's, where the project's setup installed it). Never the interpreter that runs
    foureyes itself: the plugin and `uv tool` install it apart, without the project or pytest."""
    for venv in (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe"):
        if venv.exists():
            return str(venv.absolute())
    return shutil.which("python3") or shutil.which("python") or "python"


def suites(raw: dict) -> dict:
    """The suites by role: author, tester and protected (tests people own, no agent changes them). The first
    versions called the protected suite `invariants`; a factory.yaml that still says so works the same."""
    out = dict(raw)
    if "invariants" in out:
        out["protected"] = out.pop("invariants")
    return out


COMPANY = Path(__file__).parent / "company"


def standard(root: Path, entry: dict) -> Standard:
    paths = tuple(entry["paths"])
    if "company" in entry:
        source = COMPANY / f"{entry['company']}.md"
        if not source.exists():
            known = ", ".join(sorted(p.stem for p in COMPANY.glob("*.md")))
            raise ValueError(f"factory.yaml names the company standard `{entry['company']}`; there are: {known}")
        return Standard(paths, f"company: {entry['company']}", source)
    return Standard(paths, entry["file"], root / entry["file"])


ROLES = {"author": "sonnet", "tester": "opus", "reviewer": "sonnet"}
# The factory's own MCP server is always known; a repo adds its own servers under `mcp:` in factory.yaml.
FOUREYES_SERVER = {"command": sys.executable, "args": ["-m", "foureyes", "mcp"]}


def agents(raw: dict) -> dict:
    """Each role's model and MCP servers. An entry is a model name or {model, mcp: [server, ..]}.

    The factory's agents are hermetic: they get only the servers named here, never the ones
    installed on the computer or CI runner they happen to run on.
    """
    models, mcp = dict(ROLES), {role: () for role in ROLES}
    mcp["author"] = ("four-eyes",)
    for role, entry in raw.get("agents", {}).items():
        if isinstance(entry, str):
            models[role] = entry
        else:
            models[role] = entry.get("model", models.get(role, "sonnet"))
            mcp[role] = tuple(entry.get("mcp", []))
    servers = {"four-eyes": FOUREYES_SERVER, **raw.get("mcp", {})}
    for role, names in mcp.items():
        unknown = [n for n in names if n not in servers]
        if unknown:
            raise ValueError(f"factory.yaml: agents.{role} names MCP servers not defined under mcp: {unknown}")
    return {"models": models, "mcp": mcp, "servers": servers}
