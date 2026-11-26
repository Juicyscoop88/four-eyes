"""Mutation testing of the changed lines: inject small faults, see which suites catch them.

A test suite that stays green when the code is wrong does not prove the code is right.
Each mutant is one fault on one changed line. A mutant is caught by a suite when at
least one of its tests fails.
"""

import ast
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from gate.config import Factory
from gate.tests import run_suites

SWAP_COMPARE = {
    ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
    ast.In: ast.NotIn, ast.NotIn: ast.In,
}
SWAP_BINOP = {ast.Add: ast.Sub, ast.Sub: ast.Add}
SWAP_BOOL = {ast.And: ast.Or, ast.Or: ast.And}
SYMBOL = {
    ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<=", ast.Eq: "==", ast.NotEq: "!=",
    ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in",
    ast.Add: "+", ast.Sub: "-", ast.And: "and", ast.Or: "or",
}


@dataclass
class Mutant:
    path: str
    line: int
    description: str
    source: str
    caught_by: set[str] = field(default_factory=set)


class _Apply(ast.NodeTransformer):
    """Applies the n-th possible mutation on the given lines, counting as it walks."""

    def __init__(self, lines: set[int], target: int):
        self.lines, self.target, self.seen = lines, target, 0
        self.done: tuple[int, str] | None = None

    def _hit(self, node: ast.AST) -> bool:
        if getattr(node, "lineno", None) not in self.lines:
            return False
        hit = self.seen == self.target
        self.seen += 1
        return hit

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            new = SWAP_COMPARE.get(type(op))
            if new and self._hit(node):
                node.ops[i] = new()
                self.done = (node.lineno, f"`{SYMBOL[type(op)]}` became `{SYMBOL[new]}`")
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        new = SWAP_BINOP.get(type(node.op))
        if new and self._hit(node):
            self.done = (node.lineno, f"`{SYMBOL[type(node.op)]}` became `{SYMBOL[new]}`")
            node.op = new()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        new = SWAP_BOOL.get(type(node.op))
        if new and self._hit(node):
            self.done = (node.lineno, f"`{SYMBOL[type(node.op)]}` became `{SYMBOL[new]}`")
            node.op = new()
        return node

    def visit_Raise(self, node):
        if self._hit(node):
            self.done = (node.lineno, "a `raise` was removed (a guard that no longer guards)")
            return ast.copy_location(ast.Pass(), node)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._hit(node):
            self.done = (node.lineno, "a `not` was removed")
            return node.operand
        return node


def mutants_of(path: str, source: str, lines: set[int]) -> list[Mutant]:
    out, n = [], 0
    while True:
        tree = ast.parse(source)
        applier = _Apply(lines, n)
        tree = applier.visit(tree)
        if applier.done is None:
            return out
        line, what = applier.done
        out.append(Mutant(path, line, what, ast.unparse(ast.fix_missing_locations(tree))))
        n += 1


def run(factory: Factory, workdir: Path, targets: dict[str, set[int]]) -> list[Mutant]:
    """Mutate each changed line of each target file in workdir, one mutant at a time."""
    mutants = []
    for path, lines in targets.items():
        original = (workdir / path).read_text()
        for m in mutants_of(path, original, lines):
            (workdir / path).write_text(m.source)
            failures, _ = run_suites(factory, workdir)
            m.caught_by = {f.suite for f in failures}
            mutants.append(m)
        (workdir / path).write_text(original)
    shutil.rmtree(workdir / ".hypothesis", ignore_errors=True)
    return mutants
