#!/usr/bin/env python3
"""Group the commits in a git range by conventional-commit type.

Usage: collect_commits.py [--from REF] [--to REF] [--repo DIR] [--format markdown|json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

SECTIONS = {
    "feat": "Added", "feature": "Added",
    "fix": "Fixed", "bugfix": "Fixed",
    "perf": "Performance",
    "docs": "Documentation",
    "refactor": "Internal", "test": "Internal", "tests": "Internal", "build": "Internal",
    "ci": "Internal", "chore": "Internal", "style": "Internal",
}
ORDER = ["Breaking changes", "Added", "Fixed", "Performance", "Documentation", "Internal", "Other"]
SUBJECT = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<text>.+)$")
RECORD, FIELD = "\x1e", "\x1f"


def git(repo: str, *args: str) -> str:
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def latest_tag(repo: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", repo, "describe", "--tags", "--abbrev=0"], capture_output=True, text=True
    )
    return result.stdout.strip() or None if result.returncode == 0 else None


def classify(subject: str, body: str) -> dict:
    """Return section, display text and breaking flag for one commit."""
    match = SUBJECT.match(subject)
    breaking = bool(re.search(r"^BREAKING[ -]CHANGE:", body, re.MULTILINE))
    if not match or match.group("type").lower() not in SECTIONS:
        return {"section": "Other", "text": subject, "breaking": breaking}
    text = match.group("text")
    if match.group("scope"):
        text = f"**{match.group('scope')}:** {text}"
    return {
        "section": SECTIONS[match.group("type").lower()],
        "text": text,
        "breaking": breaking or bool(match.group("bang")),
    }


def collect(repo: str, start: str | None, end: str) -> list[dict]:
    revision = f"{start}..{end}" if start else end
    log = git(repo, "log", "--no-merges", f"--format=%h{FIELD}%s{FIELD}%b{RECORD}", revision)
    commits = []
    for record in log.split(RECORD):
        if not record.strip():
            continue
        short_hash, subject, body = record.strip("\n").split(FIELD, 2)
        commits.append({"hash": short_hash, "subject": subject, **classify(subject, body)})
    return commits


def group(commits: list[dict]) -> dict[str, list[dict]]:
    sections: dict[str, list[dict]] = {name: [] for name in ORDER}
    for commit in commits:
        if commit["breaking"]:
            sections["Breaking changes"].append(commit)
        sections[commit["section"]].append(commit)
    return {name: items for name, items in sections.items() if items}


def to_markdown(sections: dict[str, list[dict]], start: str | None, end: str) -> str:
    lines = [f"# Changes {start + '..' if start else 'up to '}{end}", ""]
    if not sections:
        lines.append("No commits in this range.")
    for name, commits in sections.items():
        lines.append(f"## {name}")
        lines.extend(f"- {commit['text']} ({commit['hash']})" for commit in commits)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="start", help="start ref, exclusive (default: latest tag)")
    parser.add_argument("--to", dest="end", default="HEAD", help="end ref, inclusive (default: HEAD)")
    parser.add_argument("--repo", default=".", help="path to the git repository (default: .)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    start = args.start or latest_tag(args.repo)
    sections = group(collect(args.repo, start, args.end))
    if args.format == "json":
        print(json.dumps({"from": start, "to": args.end, "sections": sections}, indent=2))
    else:
        sys.stdout.write(to_markdown(sections, start, args.end))
    return 0


if __name__ == "__main__":
    sys.exit(main())
