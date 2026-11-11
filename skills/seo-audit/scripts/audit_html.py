#!/usr/bin/env python3
"""Audit .html files for on-page SEO problems.

Usage: audit_html.py PATH [--format text|json]     (PATH is a file or a directory)
Exit status: 1 if any error-level problem is found, otherwise 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from html.parser import HTMLParser

TITLE_MAX = 60
DESCRIPTION_MIN, DESCRIPTION_MAX = 50, 160


class PageFacts(HTMLParser):
    """Collects the handful of facts the rules need from one HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.lang = False
        self.viewport = False
        self.canonical = False
        self.noindex = False
        self.h1_count = 0
        self.images_without_alt: list[int] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: (value or "") for name, value in attrs}
        if tag == "html" and attributes.get("lang", "").strip():
            self.lang = True
        elif tag == "title" and self.title is None:
            self._in_title, self.title = True, ""
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img" and "alt" not in attributes:
            self.images_without_alt.append(self.getpos()[0])
        elif tag == "meta":
            name = attributes.get("name", "").lower()
            content = attributes.get("content", "").strip()
            if name == "description" and self.description is None:
                self.description = content
            elif name == "viewport":
                self.viewport = True
            elif name in ("robots", "googlebot") and "noindex" in content.lower():
                self.noindex = True
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = bool(attributes.get("href", "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data


def audit_page(html: str) -> tuple[PageFacts, list[dict]]:
    facts = PageFacts()
    facts.feed(html)
    problems: list[dict] = []

    def add(level: str, rule: str, message: str, line: int = 1) -> None:
        problems.append({"level": level, "rule": rule, "message": message, "line": line})

    title = " ".join((facts.title or "").split())
    facts.title = title
    if not title:
        add("error", "title-missing", "page has no <title>")
    elif len(title) > TITLE_MAX:
        add("warning", "title-length", f"title is {len(title)} characters (over {TITLE_MAX})")

    description = facts.description or ""
    if not description:
        add("error", "description-missing", "page has no meta description")
    elif not DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX:
        add("warning", "description-length",
            f"meta description is {len(description)} characters (aim for {DESCRIPTION_MIN} to {DESCRIPTION_MAX})")

    if facts.h1_count == 0:
        add("error", "h1-missing", "page has no <h1>")
    elif facts.h1_count > 1:
        add("warning", "h1-multiple", f"page has {facts.h1_count} <h1> elements")
    for line in facts.images_without_alt:
        add("error", "img-alt-missing", "<img> has no alt attribute", line)
    if not facts.lang:
        add("warning", "lang-missing", "<html> has no lang attribute")
    if not facts.viewport:
        add("warning", "viewport-missing", "no viewport meta tag")
    if not facts.canonical:
        add("warning", "canonical-missing", "no canonical link")
    if facts.noindex:
        add("warning", "noindex", "robots meta tag contains noindex")
    return facts, problems


def html_files(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    found = []
    for directory, subdirs, filenames in os.walk(path):
        subdirs[:] = sorted(d for d in subdirs if d != "node_modules")
        found.extend(os.path.join(directory, f) for f in sorted(filenames) if f.lower().endswith((".html", ".htm")))
    return found


def audit(path: str) -> list[dict]:
    """Audit every HTML file under ``path``; returns one entry per page."""
    base = path if os.path.isdir(path) else os.path.dirname(path) or "."
    pages, by_title, by_description = [], {}, {}
    for file in html_files(path):
        with open(file, encoding="utf-8", errors="replace") as handle:
            facts, problems = audit_page(handle.read())
        page = {"path": os.path.relpath(file, base), "problems": problems}
        pages.append(page)
        if facts.title:
            by_title.setdefault(facts.title, []).append(page)
        if facts.description:
            by_description.setdefault(facts.description, []).append(page)

    for rule, label, groups in (
        ("title-duplicate", "title", by_title),
        ("description-duplicate", "meta description", by_description),
    ):
        for group in groups.values():
            for page in group if len(group) > 1 else []:
                others = ", ".join(other["path"] for other in group if other is not page)
                page["problems"].append(
                    {"level": "warning", "rule": rule, "message": f"same {label} as {others}", "line": 1}
                )
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="an HTML file or a directory to search for .html files")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if not os.path.exists(args.path):
        print(f"audit_html: no such file or directory: {args.path}", file=sys.stderr)
        return 2
    pages = audit(args.path)
    if not pages:
        print(f"audit_html: no .html files found in {args.path}", file=sys.stderr)
        return 2

    errors = sum(p["level"] == "error" for page in pages for p in page["problems"])
    warnings = sum(p["level"] == "warning" for page in pages for p in page["problems"])
    if args.format == "json":
        print(json.dumps({"pages": pages, "errors": errors, "warnings": warnings}, indent=2))
    else:
        for page in pages:
            for problem in page["problems"]:
                print(f"{page['path']}:{problem['line']}: {problem['level']}: {problem['message']} [{problem['rule']}]")
        print(f"\n{len(pages)} page(s) checked: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
