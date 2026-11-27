"""Tests of the gate itself (not a suite the gate measures)."""

import json
from pathlib import Path

from foureyes.agents import stub_source
from foureyes.check import invariant_of
from foureyes.config import load
from foureyes.hooks import pre_tool_use
from foureyes.mutation import mutants_of
from foureyes.tests import Failure

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
    assert factory.is_owned("tools/foureyes/check.py")
    assert not factory.is_owned("src/orders/engine.py")
    assert factory.suite_of("tests/blind/test_x.py") == "tester"


def test_a_broken_invariant_is_named():
    f = Failure("invariants", "test_never_overfilled", "AssertionError: ORD-1: filled 3 of 2")
    assert invariant_of(factory, f).statement == "An order is never filled beyond its quantity."
    assert invariant_of(factory, Failure("author", "t", "ORD-1: x")) is None


def decision(capsys, tool_input, tool="Edit"):
    import uuid

    path = tool_input.get("file_path")
    if path:  # a path already read in this session: only the rules of owned files and secrets apply
        pre_tool_use(factory, {"tool_name": "Read", "tool_input": {"file_path": path}, "session_id": "t"})
        capsys.readouterr()
    pre_tool_use(factory, {"tool_name": tool, "tool_input": tool_input, "session_id": "t"})
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"].get("permissionDecision", "allow") if out else "allow"


def test_the_first_touch_of_a_path_brings_its_rules(capsys):
    import uuid

    session = uuid.uuid4().hex
    read = {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "src/orders/model.py")}, "session_id": session}
    pre_tool_use(factory, read)
    first = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "ORD-1" in first and "money.md" in first
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "src/orders/model.py"), "new_string": "x"},
            "session_id": session}
    pre_tool_use(factory, edit)
    assert capsys.readouterr().out == ""  # read first: the edit goes through, the rules came once
    new = {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "src/orders/new.py"), "content": "x"},
           "session_id": session}
    pre_tool_use(factory, new)
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert "permissionDecision" not in out and "money.md" in out["additionalContext"]  # a new file: rules, no refusal


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


def test_mutants_reach_arithmetic_constants_and_rounding():
    code = "x = round(a * b / 10**6, ROUND_HALF_EVEN)\n"
    found = {m.description for m in mutants_of("x.py", code, {1})}
    assert {"`*` became `/`", "`/` became `*`", "`10` became `11`", "`ROUND_HALF_EVEN` became `ROUND_HALF_UP`",
            "the call to `round()` was removed"} <= found
    assert mutants_of("x.py", '"""Doc 6."""\n', {1}) == []


def test_cards_travel_in_the_comment():
    from foureyes.check import cards_from

    cards = [{"where": "a.py:1", "why": "w", "question": "q?", "options": ["keep: x", "reject: y"]}]
    comment = "## FourEyes gate\n...\n<!-- four-eyes-cards " + json.dumps(cards) + " -->\n"
    assert cards_from(comment) == cards
    assert cards_from("no cards") == []


def test_rules_for_names_owners_invariants_and_standards():
    from foureyes.rules import rules_for

    money = rules_for(factory, "src/orders/engine.py")
    assert "tier **money**" in money and "ORD-1" in money and "Money in code" not in money.split("##")[0]
    assert "standards/money.md" in money
    app = rules_for(factory, "apps/recon/page.tsx")
    assert "design-system" in app and "optimistic-ui" in app and "ORD-1" not in app
    assert "Owned by people" in rules_for(factory, "invariants/orders.yaml")


def test_assumptions_become_cards():
    from foureyes.check import Result, assumptions_of

    task = "# T\n\n## Assumptions\n\n1. **Total.** With 4 of 10\n   filled, 12 leaves 8.\n2. NaN is rejected.\n\n## Decisions\n"
    assert assumptions_of(task) == ["**Total.** With 4 of 10 filled, 12 leaves 8.", "NaN is rejected."]
    res = Result("b", [], "money")
    res.assumptions = assumptions_of(task)
    assert [c["id"] for c in res.cards()] == ["A1", "A2"]


def test_assumptions_in_any_list_style():
    from foureyes.check import assumptions_of

    task = "## Assumptions\n\n- A1. Limit price.\n- A2. No rounding.\n* 3) Zero fills.\n"
    assert assumptions_of(task) == ["Limit price.", "No rounding.", "Zero fills."]


def test_agents_are_hermetic_with_only_the_servers_factory_yaml_names(tmp_path):
    from foureyes.config import agents

    repo = load(Path(__file__).resolve().parents[2])
    assert repo.models == {"author": "sonnet", "tester": "opus", "reviewer": "sonnet"}
    assert repo.mcp == {"author": ("foureyes",), "tester": (), "reviewer": ()}
    # A plain model name still works, and a repo adds its own server for one role.
    got = agents({"agents": {"tester": "haiku", "author": {"mcp": ["foureyes", "gitlab"]}},
                  "mcp": {"gitlab": {"command": "gitlab-mcp"}}})
    assert got["models"]["tester"] == "haiku" and got["mcp"]["tester"] == ()
    assert got["mcp"]["author"] == ("foureyes", "gitlab") and "gitlab" in got["servers"]


def test_a_role_naming_an_undefined_server_fails_loudly():
    import pytest
    from foureyes.config import agents

    with pytest.raises(ValueError, match="neon"):
        agents({"agents": {"author": {"mcp": ["neon"]}}})


def test_the_testers_open_questions_never_block():
    from foureyes.check import is_open

    assert is_open("tests/blind/test_x.py::test_open_exactly_365_days")
    assert is_open("test_open_rounding[ru-1100]")
    assert not is_open("tests/blind/test_x.py::test_rounds_up_to_next_year")
