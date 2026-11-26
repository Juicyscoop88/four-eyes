"""gate: the Four Eyes command. The same in a terminal, in Claude Code (/ship) and in GitLab CI."""

import argparse
import os
import sys
from pathlib import Path

from gate import agents, hooks
from gate.check import check, report
from gate.config import load
from gate.diff import git


def repo_root() -> Path:
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())


def read_task(arg: str | None) -> str | None:
    if arg:
        return Path(arg).read_text()
    # In CI the task is the merge request or pull request description.
    return os.environ.get("FACTORY_TASK") or os.environ.get("CI_MERGE_REQUEST_DESCRIPTION") or None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="what this change must prove before it merges")
    c.add_argument("--base", default=os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", "main"))
    c.add_argument("--task", help="the task as a file (in CI: the merge request or pull request description)")
    c.add_argument("--agents", action="store_true", help="also run the reviewer agent")
    c.add_argument("--report", default="gate-report.md")

    t = sub.add_parser("tests", help="the tester writes tests for a task, without seeing the code")
    t.add_argument("--task", required=True)
    t.add_argument("--name", help="test file name (default: the task file name)")

    a = sub.add_parser("autopilot", help="a person wrote the issue; the factory does the rest, on a branch")
    a.add_argument("issue", help="the issue as a Markdown file")
    a.add_argument("--rounds", type=int, default=4)

    e = sub.add_parser("eval", help="plant realistic bugs in finished tasks, see what catches them")
    e.add_argument("tasks", nargs="+", help="slugs of factory/<slug> branches")
    e.add_argument("--bugs", type=int, default=5)
    e.add_argument("--testers", default="haiku,sonnet,opus")

    d = sub.add_parser("decide", help="a person answers a decision card; it becomes a test, then code")
    d.add_argument("slug", help="the task, as in factory/<slug>")
    d.add_argument("card", type=int)
    d.add_argument("answer", nargs="+")
    d.add_argument("--by", default=os.environ.get("FACTORY_REQUESTED_BY"))
    d.add_argument("--comment", help="a file with the gate comment the person answered (its cards are used)")

    w = sub.add_parser("why", help="why a line exists: issue, who asked, decisions, tests that pin it, approval")
    w.add_argument("where", help="path:line")

    sub.add_parser("rules", help="what applies to a path").add_argument("path")
    sub.add_parser("mcp", help="run the FourEyes MCP server on stdio (Claude Code starts it from the plugin)")

    h = sub.add_parser("hook", help="Claude Code hooks of the plugin (read the event on stdin)")
    h.add_argument("event", choices=["pre-tool-use", "stop"])

    args = p.parse_args(argv)
    factory = load(repo_root())

    if args.cmd == "why":
        from gate.why import why

        path, line = args.where.rsplit(":", 1)
        print(why(factory, path, int(line)))
        return 0

    if args.cmd == "rules":
        from gate.rules import rules_for

        print(rules_for(factory, args.path))
        return 0

    if args.cmd == "mcp":
        from gate.mcp_server import main as serve

        serve()
        return 0

    if args.cmd == "hook":
        return hooks.handle(factory, args.event, sys.stdin.read())

    if args.cmd == "autopilot":
        from gate.autopilot import Pilot

        path = Pilot(factory, Path(args.issue).resolve(), log=lambda m: print(m, flush=True)).run(args.rounds)
        print(f"autopilot: report in {path.relative_to(factory.root)}")
        return 0

    if args.cmd == "decide":
        from gate.autopilot import Pilot

        from gate.check import author_of

        who = args.by or author_of(factory.root)
        pilot = Pilot(factory, factory.root / "issues" / f"{args.slug}.md", log=lambda m: print(m, flush=True))
        from gate.check import cards_from

        cards = cards_from(Path(args.comment).read_text()) if args.comment else None
        path = pilot.decide(args.card, " ".join(args.answer), who, cards)
        print(f"decide: report in {path.relative_to(factory.root)}")
        return 0

    if args.cmd == "eval":
        import json as _json

        from gate.eval import evaluate, summary

        testers = args.testers.split(",")
        results = [evaluate(factory, t, args.bugs, testers, log=lambda m: print(m, flush=True)) for t in args.tasks]
        out = factory.root / "docs" / "eval.md"
        out.write_text(summary(results, testers))
        (factory.root / "docs" / "eval.json").write_text(_json.dumps(results, indent=2))
        print(out.read_text())
        return 0

    if args.cmd == "tests":
        name = args.name or Path(args.task).stem.replace("-", "_")
        print(f"tester: writing tests for {args.task}, in a workspace without the implementation")
        run, written = agents.write_blind_tests(factory, Path(args.task).read_text(), name)
        print(run.result.strip())
        print(f"tester: wrote {', '.join(written) or 'nothing'} (${run.cost_usd:.3f}, {run.turns} turns)")
        return 0 if written else 1

    res = check(factory, args.base, read_task(args.task), args.agents, log=lambda m: print(m, file=sys.stderr))
    text = report(factory, res, git(factory.root, "rev-parse", "HEAD").strip())
    Path(factory.root / args.report).write_text(text)
    print(text)
    return 0 if res.passed else 1


if __name__ == "__main__":
    sys.exit(main())
