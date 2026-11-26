"""factory.yaml: the one file per repo the gate reads."""

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
class Invariant:
    id: str
    statement: str
    why: str
    test: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Standard:
    paths: tuple[str, ...]
    file: str


@dataclass(frozen=True)
class Factory:
    root: Path
    owned: list[str]
    suites: dict[str, str]
    tiers: list[Tier]
    invariants: list[Invariant]
    models: dict[str, str]  # role -> model; the tester differs from the author on purpose
    standards: list[Standard]

    def is_owned(self, path: str) -> bool:
        return any(matches(path, p) for p in self.owned)

    def tier_of(self, path: str) -> Tier:
        for tier in self.tiers:
            if any(matches(path, p) for p in tier.paths):
                return tier
        return self.tiers[-1]

    def suite_of(self, test_path: str) -> str | None:
        for name, folder in self.suites.items():
            if test_path == folder or test_path.startswith(folder.rstrip("/") + "/"):
                return name
        return None

    def invariant(self, inv_id: str) -> Invariant | None:
        return next((i for i in self.invariants if i.id == inv_id), None)


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
    invariants = []
    for file in raw.get("invariants", []):
        doc = yaml.safe_load((root / file).read_text())
        paths = tuple(doc.get("paths", []))
        invariants += [Invariant(i["id"], i["statement"], i["why"], i["test"], paths) for i in doc["invariants"]]
    return Factory(
        root=root,
        owned=raw.get("owned", []),
        suites=raw["suites"],
        tiers=tiers,
        invariants=invariants,
        standards=[Standard(tuple(x["paths"]), x["file"]) for x in raw.get("standards", [])],
        models={"author": "sonnet", "tester": "opus", "reviewer": "sonnet", **raw.get("agents", {})},
    )
