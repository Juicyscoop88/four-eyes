"""foureyes: the Four Eyes command. The same on a laptop and in CI: one small function per command."""

import argparse
import os
import sys
from pathlib import Path

from foureyes import hooks
from foureyes.check import check
from foureyes.config import load
from foureyes.report import report
from foureyes.diff import git


def repo_root() -> Path:
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())


def read_task(arg: str | None) -> str | None:
    if arg:
        return Path(arg).read_text()
    # In CI the task is the merge request or pull request description.
    return os.environ.get("FACTORY_TASK") or os.environ.get("CI_MERGE_REQUEST_DESCRIPTION") or None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="foureyes")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="what this change must prove before it merges")
    c.add_argument("--base", default=os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", "main"))
    c.add_argument("--task", help="the task as a file (in CI: the merge request or pull request description)")
    c.add_argument("--agents", action="store_true", help="also run the reviewer agent")
    c.add_argument("--report", default="gate-report.md")

    a = sub.add_parser("autopilot", help="a person wrote the issue; the factory does the rest, on a branch")
    a.add_argument("issue", help="the issue as a Markdown file")
    a.add_argument("--rounds", type=int, default=4)

    e = sub.add_parser("eval", help="plant realistic bugs in finished tasks, see what catches them")
    e.add_argument("tasks", nargs="+", help="slugs of factory/<slug> branches")
    e.add_argument("--bugs", type=int, default=5)
    e.add_argument("--testers", default="haiku,sonnet,opus")

    d = sub.add_parser("decide", help="a person answers a decision card; it becomes a test, then code")
    d.add_argument("slug", help="the task, as in factory/<slug>")
    d.add_argument("card", help="1, 2, 3 for the reviewer's cards, A1, A2.. for the plan's assumptions")
    d.add_argument("answer", nargs="+")
    d.add_argument("--by", default=os.environ.get("FACTORY_REQUESTED_BY"))
    d.add_argument("--comment", help="a file with the gate comment the person answered (its cards are used)")
    d.add_argument("--branch", default="", help="the pull request's branch, when the autopilot did not make it")
    d.add_argument("--description", default=os.environ.get("FACTORY_TASK", ""),
                   help="the pull request's description: the task, when there is no task file")

    sub.add_parser("company", help="the company's settings: its GitHub organisation and who adopts self-built tools")

    m = sub.add_parser("summary", help="the team's last days in numbers, from the gate reports on the pull requests")
    m.add_argument("--days", type=int, default=7)

    sub.add_parser("mcp", help="run the factory's MCP server on stdio (Claude Code starts it from the plugin)")

    h = sub.add_parser("hook", help="Claude Code hooks of the plugin (read the event on stdin)")
    h.add_argument("event", choices=["session-start", "pre-tool-use", "stop"])

    args = p.parse_args(argv)
    return COMMANDS[args.cmd](args)


def log(message: str) -> None:
    print(message, flush=True)


def cmd_check(args) -> int:
    factory = load(repo_root())
    res = check(factory, args.base, read_task(args.task), args.agents, log=lambda m: print(m, file=sys.stderr))
    text = report(factory, res, git(factory.root, "rev-parse", "HEAD").strip())
    Path(factory.root / args.report).write_text(text)
    print(text)
    return 0 if res.passed else 1


def cmd_autopilot(args) -> int:
    from foureyes.autopilot import Pilot

    factory = load(repo_root())
    path = Pilot(factory, Path(args.issue).resolve(), log=log).run(args.rounds)
    print(f"autopilot: report in {path.relative_to(factory.root)}")
    return 0


def cmd_decide(args) -> int:
    from foureyes.autopilot import Pilot
    from foureyes.report import author_of, cards_from

    factory = load(repo_root())
    pilot = Pilot(factory, factory.root / "issues" / f"{args.slug}.md", log=log)
    cards = cards_from(Path(args.comment).read_text()) if args.comment else None
    path = pilot.decide(args.card, " ".join(args.answer), args.by or author_of(factory.root), cards,
                        branch=args.branch, description=args.description)
    print(f"decide: report in {path.relative_to(factory.root)}")
    return 0


def cmd_eval(args) -> int:
    import json

    from foureyes.eval import evaluate, summary

    factory = load(repo_root())
    testers = args.testers.split(",")
    results = [evaluate(factory, t, args.bugs, testers, log=log) for t in args.tasks]
    out = factory.root / "docs" / "eval.md"
    out.write_text(summary(results, testers))
    (factory.root / "docs" / "eval.json").write_text(json.dumps(results, indent=2))
    print(out.read_text())
    return 0


def cmd_company(args) -> int:
    from foureyes.config import COMPANY

    print((COMPANY / "company.yaml").read_text(), end="")
    return 0


def cmd_summary(args) -> int:
    from foureyes.summary import fetch, summarize

    print(summarize(fetch(args.days), args.days), end="")
    return 0


def cmd_mcp(args) -> int:
    from foureyes.mcp_server import main as serve

    serve()
    return 0


def cmd_hook(args) -> int:
    # The plugin is a person's, the repo may not use Four Eyes: then its hooks stay silent, except one line at the
    # start of a session, so Claude can offer setup once when the person builds something others depend on.
    import subprocess

    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    root = Path(top or Path.cwd())
    if not (root / "factory.yaml").exists():
        return hooks.context("SessionStart", hooks.NOT_SET_UP) if args.event == "session-start" else 0
    return hooks.handle(load(root), args.event, sys.stdin.read())


COMMANDS = {
    "check": cmd_check, "autopilot": cmd_autopilot, "decide": cmd_decide, "eval": cmd_eval,
    "company": cmd_company, "summary": cmd_summary, "mcp": cmd_mcp, "hook": cmd_hook,
}


if __name__ == "__main__":
    sys.exit(main())
