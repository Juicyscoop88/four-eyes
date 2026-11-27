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
    assert "ORD-1" in first and "Company standard: money" in first
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "src/orders/model.py"), "new_string": "x"},
            "session_id": session}
    pre_tool_use(factory, edit)
    assert capsys.readouterr().out == ""  # read first: the edit goes through, the rules came once
    new = {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "src/orders/new.py"), "content": "x"},
           "session_id": session}
    pre_tool_use(factory, new)
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert "permissionDecision" not in out and "Company standard: money" in out["additionalContext"]  # a new file: rules, no refusal


def test_hook_keeps_agents_off_owned_files(capsys):
    assert decision(capsys, {"file_path": str(ROOT / "invariants/orders.yaml"), "new_string": "x"}) == "deny"
    assert decision(capsys, {"file_path": str(ROOT / "tests/invariants/test_orders.py")}, "Write") == "deny"
    assert decision(capsys, {"file_path": str(ROOT / "src/orders/engine.py"), "new_string": "x = 1"}) == "allow"
    assert decision(capsys, {"command": "ls"}, "Bash") == "allow"


def test_a_new_owned_file_can_be_drafted_until_it_is_committed(capsys):
    # Setup wrote factory.yaml, saw a wrong line and could not fix it: the file was locked the moment it existed.
    assert decision(capsys, {"file_path": str(ROOT / "invariants/a_new_draft.yaml"), "content": "x"}, "Write") == "allow"
    assert decision(capsys, {"file_path": str(ROOT / "factory.yaml"), "new_string": "x"}) == "deny"


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
    assert "Company standard: money" in money and "Company standard: basics" in money
    app = rules_for(factory, "apps/recon/page.tsx")
    assert "Company standard: design-system" in app and "Standard: standards/optimistic-ui.md" in app
    assert "ORD-1" not in app
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
    assert repo.mcp == {"author": ("factory",), "tester": (), "reviewer": ()}
    # A plain model name still works, and a repo adds its own server for one role.
    got = agents({"agents": {"tester": "haiku", "author": {"mcp": ["factory", "gitlab"]}},
                  "mcp": {"gitlab": {"command": "gitlab-mcp"}}})
    assert got["models"]["tester"] == "haiku" and got["mcp"]["tester"] == ()
    assert got["mcp"]["author"] == ("factory", "gitlab") and "gitlab" in got["servers"]


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


def test_a_venv_python_is_kept_as_its_link_not_the_system_python_behind_it(tmp_path):
    # uv makes .venv/bin/python a link to the interpreter it was built from. Following that link loses
    # the venv (and its pytest), so the gate saw a broken invariant where the code was fine.
    import shutil
    import sys

    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").symlink_to(sys.executable)
    text = (ROOT / "factory.yaml").read_text()
    (tmp_path / "factory.yaml").write_text(text + "\npython: .venv/bin/python\n")
    for file in yaml_list(text, "invariants"):
        (tmp_path / file).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / file, tmp_path / file)
    assert load(tmp_path).python == str(tmp_path / ".venv" / "bin" / "python")


def yaml_list(text: str, key: str) -> list[str]:
    import yaml

    return yaml.safe_load(text).get(key, [])


def test_a_company_standard_ships_with_the_factory_and_an_unknown_one_fails_loudly(tmp_path):
    import pytest
    from foureyes.config import standard

    design = standard(tmp_path, {"paths": ["apps/**"], "company": "design-system"})
    assert design.company and "Design system" in design.text()   # nothing copied into the repo
    with pytest.raises(ValueError, match="design-sytem.*basics, design-system, money"):
        standard(tmp_path, {"paths": ["apps/**"], "company": "design-sytem"})


def small_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """A git repo with a factory.yaml, the given files committed on `main`."""
    import subprocess

    (tmp_path / "factory.yaml").write_text(
        "owned: [factory.yaml]\nsource: src\n"
        "suites: {author: tests, tester: tests/blind, invariants: tests/invariants}\n"
        "tiers: {money: {paths: ['src/**'], mutation_min: 0.5}, low: {paths: ['**'], mutation_min: 0.0}}\n"
    )
    for path, text in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text)
    for cmd in (["init", "-q", "-b", "main"], ["add", "-A"],
                ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        subprocess.run(["git", *cmd], cwd=tmp_path, check=True)
    return tmp_path


def test_a_test_that_failed_before_the_change_is_reported_and_never_blocks(tmp_path):
    # A mature repo often carries a red test nobody fixed yet. It blocked every pull request and sent the
    # autopilot's author off to fix someone else's test (pandas_market_calendars, a time zone test).
    from foureyes.check import check

    root = small_repo(tmp_path, {
        "src/calc.py": "def double(x):\n    return x * 2\n",
        "tests/test_old.py": "def test_red_before():\n    assert False, 'red on main'\n",
    })
    (root / "src/calc.py").write_text("def double(x):\n    return x * 2\n\n\ndef triple(x):\n    return x * 3\n")
    (root / "tests/test_calc.py").write_text("from calc import triple\n\n\ndef test_triple():\n    assert triple(2) == 6\n")
    res = check(load(root), "main", None, False, log=lambda m: None)
    assert [f.test for f in res.preexisting] == ["test_red_before"]
    assert not res.failures
    assert not any("author" in b for b in res.blocks)


def test_a_broken_invariant_blocks_even_when_it_was_red_before(tmp_path):
    from foureyes.check import check

    root = small_repo(tmp_path, {
        "src/calc.py": "def double(x):\n    return x * 2\n",
        "tests/invariants/test_inv.py": "def test_inv():\n    assert False, 'red on main'\n",
    })
    (root / "src/calc.py").write_text("def double(x):\n    return x * 2 + 0\n")
    res = check(load(root), "main", None, False, log=lambda m: None)
    assert [f.test for f in res.failures] == ["test_inv"] and not res.preexisting and res.blocks


def test_a_test_this_change_breaks_still_blocks(tmp_path):
    from foureyes.check import check

    root = small_repo(tmp_path, {
        "src/calc.py": "def double(x):\n    return x * 2\n",
        "tests/test_calc.py": "from calc import double\n\n\ndef test_double():\n    assert double(2) == 4\n",
    })
    (root / "src/calc.py").write_text("def double(x):\n    return x + 2 + 1\n")
    res = check(load(root), "main", None, False, log=lambda m: None)
    assert [f.test for f in res.failures] == ["test_double"] and not res.preexisting
    assert res.blocks


def test_each_mutant_runs_only_the_tests_the_gate_uses(tmp_path):
    # Every mutant ran the whole repo (1700 tests, 50 s each): 32 mutants took 25 minutes. Only the independent
    # suites count and the change's own tests are measured; the rest of the repo decides nothing.
    from foureyes.check import check

    root = small_repo(tmp_path, {
        "src/calc.py": "def double(x):\n    return x * 2\n",
        # The rest of the repo: had it run against a mutant, it would show up as a catch by the author's suite.
        "tests/test_rest_of_repo.py": "def test_always_red():\n    assert False\n",
    })
    (root / "src/calc.py").write_text("def double(x):\n    return x * 2\n\n\ndef triple(x):\n    return x * 3\n")
    (root / "tests/blind").mkdir()
    (root / "tests/blind/test_triple.py").write_text("from calc import triple\n\n\ndef test_triple():\n    assert triple(2) == 6\n")
    res = check(load(root), "main", None, False, log=lambda m: None)
    assert len(res.mutants) == 2 and all(m.caught_by == {"tester"} for m in res.mutants)


def test_a_hand_made_change_gets_blind_tests_from_the_gate(tmp_path, monkeypatch):
    # design.md promised it, the gate did not: a change written by hand had only its author's tests.
    from foureyes import agents
    from foureyes.check import check

    def tester(factory, task, name, gaps=(), model=None, dest_root=None, fresh=False):
        (dest_root / "tests/blind").mkdir(parents=True, exist_ok=True)
        (dest_root / "tests/blind/test_this_change.py").write_text(
            "from calc import triple\n\n\ndef test_triple():\n    assert triple(2) == 6\n")
        return agents.AgentRun("tester", "haiku", "", 0.01, 1), ["tests/blind/test_this_change.py"]

    def reviewer(factory, task, diff, facts):
        return agents.Review(agents.AgentRun("reviewer", "haiku", "", 0.01, 1), [], [], "")

    monkeypatch.setattr(agents, "write_blind_tests", tester)
    monkeypatch.setattr(agents, "review", reviewer)
    root = small_repo(tmp_path, {"src/calc.py": "def double(x):\n    return x * 2\n"})
    (root / "src/calc.py").write_text("def double(x):\n    return x * 2\n\n\ndef triple(x):\n    return x * 3\n")
    res = check(load(root), "main", "Add triple.", True, log=lambda m: None)
    assert res.blind_written == ["tests/blind/test_this_change.py"]
    assert res.mutants and all("tester" in m.caught_by for m in res.mutants)
    assert not (root / "tests/blind").exists()  # the branch is unchanged


def test_an_owned_file_is_locked_unless_git_says_it_is_new(tmp_path):
    # Card 1 of PR #20 (deny-in-repo): a fresh `git init` drafts freely, a folder git cannot read stays locked.
    import subprocess

    from foureyes.hooks import committed

    assert committed(tmp_path, "factory.yaml")  # not a repo: git cannot answer, so it counts as committed
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert not committed(tmp_path, "factory.yaml")  # fresh repo, no commit yet
