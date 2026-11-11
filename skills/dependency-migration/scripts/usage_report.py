#!/usr/bin/env python3
"""Report where a package is imported in Python, JavaScript and TypeScript sources.

Usage: usage_report.py PACKAGE [PATH] [--format text|json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next", "vendor"}
PY_EXT = {".py", ".pyi"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}


def patterns(package: str) -> tuple[re.Pattern, re.Pattern]:
    py_name = re.escape(package.replace("-", "_"))
    js_name = re.escape(package)
    py = re.compile(
        rf"^\s*(?:from\s+{py_name}(?:\.[\w.]+)?\s+import\s+(?P<names>.+)|import\s+{py_name}(?:\.[\w.]+)?\b.*)$"
    )
    js_import = re.compile(
        rf"""(?:import\s+(?P<names>[^'"]*?)\s*from\s*|import\s*\(\s*|require\s*\(\s*|import\s+)['"]{js_name}(?:/[^'"]*)?['"]"""
    )
    return py, js_import


def imported_names(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.split("#", 1)[0].strip().strip("()")
    names = []
    for part in raw.replace("{", ",").replace("}", ",").split(","):
        words = part.split()
        if words and words[0] not in ("type", "*"):
            names.append(words[0])
        elif len(words) > 1 and words[0] == "type":
            names.append(words[1])
        elif words[:1] == ["*"]:
            names.append("*")
    return names


def scan(package: str, root: str) -> list[dict]:
    py, js_import = patterns(package)
    files = []
    for directory, subdirs, filenames in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            extension = os.path.splitext(filename)[1]
            if extension not in PY_EXT | JS_EXT:
                continue
            path = os.path.join(directory, filename)
            try:
                with open(path, encoding="utf-8") as handle:
                    lines = handle.read().splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            uses = []
            for number, line in enumerate(lines, start=1):
                match = py.match(line) if extension in PY_EXT else js_import.search(line)
                if match:
                    uses.append({"line": number, "names": imported_names(match.group("names")), "code": line.strip()})
            if uses:
                files.append({"path": os.path.relpath(path, root), "uses": uses})
    return sorted(files, key=lambda item: (-len(item["uses"]), item["path"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", help="package name as written in import statements")
    parser.add_argument("path", nargs="?", default=".", help="directory to scan (default: .)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    files = scan(args.package, args.path)
    total = sum(len(item["uses"]) for item in files)
    names: dict[str, int] = {}
    for item in files:
        for use in item["uses"]:
            for name in use["names"]:
                names[name] = names.get(name, 0) + 1

    if args.format == "json":
        print(json.dumps({"package": args.package, "imports": total, "files": files, "names": names}, indent=2))
        return 0
    print(f"{args.package}: {total} import(s) in {len(files)} file(s)")
    for item in files:
        print(f"\n{item['path']} ({len(item['uses'])})")
        for use in item["uses"]:
            print(f"  {use['line']:>4}: {use['code']}")
    if names:
        ranked = sorted(names.items(), key=lambda pair: (-pair[1], pair[0]))
        print("\nImported names: " + ", ".join(f"{name} x{count}" for name, count in ranked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
