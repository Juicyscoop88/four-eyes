"""Tests of the gate itself (not a suite the gate measures)."""

import json
from pathlib import Path

from gate.agents import stub_source
from gate.check import invariant_of
from gate.config import load
from gate.hooks import pre_tool_use
from gate.mutation import mutants_of
from gate.tests import Failure

ROOT = Path(__file__).resolve().parents[2]
factory = load(ROOT)

CODE = """\
def apply(order, qty):
    \"\"\"Apply a fill.\"\"\"
    if qty > order.remaining or not order.open:
        raise ValueError("no")
    return order.filled + qty
"""


def test_mutants_only_on_changed_lines():
    on_guard = mutants_of("x.py", CODE, {3})
    assert [m.description for m in on_guard] == [
        "`>` became `>=`", "a `not` was removed", "`or` became `and`",
    ]
    assert all(m.line == 3 for m in on_guard)
    assert [m.description for m in mutants_of("x.py", CODE, {4, 5})] == [
        "a `raise` was removed (a guard that no longer guards)", "`+` became `-`",
    ]
    assert mutants_of("x.py", CODE, {1, 2}) == []


def test_stub_keeps_the_interface_and_drops_the_implementation():
    stub = stub_source(CODE)
    assert "def apply(order, qty):" in stub
    assert "Apply a fill." in stub
    assert "raise NotImplementedError()" in stub
    assert "remaining" not in stub


def test_tiers_and_ownership():
    assert factory.tier_of("src/orders/engine.py").name == "money"
    assert factory.tier_of("src/other.py").name == "standard"
    assert factory.tier_of("README.md").name == "low"
    assert factory.is_owned("invariants/orders.yaml")
    assert factory.is_owned("tests/invariants/test_orders.py")
    assert factory.is_owned("tools/gate/check.py")
    assert not factory.is_owned("src/orders/engine.py")
    assert factory.suite_of("tests/blind/test_x.py") == "tester"


def test_a_broken_invariant_is_named():
    f = Failure("invariants", "test_never_overfilled", "AssertionError: ORD-1: filled 3 of 2")
    assert invariant_of(factory, f).statement == "An order is never filled beyond its quantity."
    assert invariant_of(factory, Failure("author", "t", "ORD-1: x")) is None


def decision(capsys, tool_input, tool="Edit"):
    pre_tool_use(factory, {"tool_name": tool, "tool_input": tool_input})
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"


def test_hook_keeps_agents_off_owned_files(capsys):
    assert decision(capsys, {"file_path": str(ROOT / "invariants/orders.yaml"), "new_string": "x"}) == "deny"
    assert decision(capsys, {"file_path": str(ROOT / "tests/invariants/test_orders.py")}, "Write") == "deny"
    assert decision(capsys, {"file_path": str(ROOT / "src/orders/engine.py"), "new_string": "x = 1"}) == "allow"
    assert decision(capsys, {"command": "ls"}, "Bash") == "allow"


def test_hook_blocks_secrets(capsys):
    key = "AKIA" + "ABCDEFGHIJKLMNOP"
    assert decision(capsys, {"file_path": str(ROOT / "src/x.py"), "content": f"KEY = '{key}'"}, "Write") == "deny"
    pem = "-----BEGIN RSA " + "PRIVATE KEY-----"
    assert decision(capsys, {"file_path": str(ROOT / "src/x.py"), "new_string": pem}) == "deny"
    ref = "KEY = secret('trading-api')"
    assert decision(capsys, {"file_path": str(ROOT / "src/x.py"), "new_string": ref}) == "allow"
