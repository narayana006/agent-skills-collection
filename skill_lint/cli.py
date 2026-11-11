"""Command-line interface: ``skill-lint [PATH ...]``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skill_lint import __version__
from skill_lint.checks import Issue, find_skills, lint_skill


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-lint",
        description="Validate agent skill folders: frontmatter, naming, links and script syntax.",
    )
    parser.add_argument(
        "paths", nargs="*", default=["skills"], metavar="PATH",
        help="a skills directory or a single skill folder (default: skills)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")
    parser.add_argument("--version", action="version", version=f"skill-lint {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results: list[tuple[str, list[Issue]]] = []
    for raw in args.paths:
        root = Path(raw)
        if not root.is_dir():
            print(f"skill-lint: not a directory: {raw}", file=sys.stderr)
            return 2
        skills = find_skills(root)
        if not skills:
            print(f"skill-lint: no skill folders found in {raw}", file=sys.stderr)
            return 2
        base = root.parent if skills == [root] else root
        results.extend((skill.name, lint_skill(skill, base)) for skill in skills)

    errors = sum(issue.level == "error" for _, issues in results for issue in issues)
    warnings = sum(issue.level == "warning" for _, issues in results for issue in issues)

    if args.format == "json":
        payload = {
            "skills": [
                {"name": name, "ok": not any(i.level == "error" for i in issues),
                 "issues": [issue.as_dict() for issue in issues]}
                for name, issues in results
            ],
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(payload, indent=2))
    else:
        for name, issues in results:
            failed = any(issue.level == "error" for issue in issues)
            print(f"{'FAIL' if failed else 'ok  '}  {name}")
            for issue in issues:
                print(f"      {issue.path}:{issue.line}: {issue.level}: {issue.message} [{issue.rule}]")
        print(f"\n{len(results)} skill(s) checked: {errors} error(s), {warnings} warning(s)")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
