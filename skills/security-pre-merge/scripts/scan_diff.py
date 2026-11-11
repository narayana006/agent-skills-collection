#!/usr/bin/env python3
"""Flag likely secrets and risky constructs on the added lines of a unified diff.

Usage: scan_diff.py [DIFF_FILE] [--format text|json]     (reads stdin when no file is given)
Exit status: 1 if any high-severity finding, otherwise 0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# (rule id, severity, description, pattern)
RULES = [
    ("private-key", "high", "private key material",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("aws-access-key", "high", "AWS access key id",
     re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("hardcoded-secret", "high", "hard-coded credential",
     re.compile(
         r"""(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\w*["']?\s*[:=]\s*["'][^"'\s]{6,}["']"""
     )),
    ("tls-verify-off", "high", "TLS certificate verification disabled",
     re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true")),
    ("shell-injection", "medium", "shell command built at run time",
     re.compile(r"shell\s*=\s*True|\bos\.system\s*\(|child_process\.exec\s*\(")),
    ("dynamic-eval", "medium", "dynamic code execution",
     re.compile(r"(?<![\w.])(?:eval|exec)\s*\(|new\s+Function\s*\(")),
    ("sql-string-building", "medium", "SQL built with string formatting",
     re.compile(r"""(?i)(?:execute|query)\s*\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format))""")),
    ("unsafe-deserialise", "medium", "deserialiser that can run code",
     re.compile(r"\bpickle\.loads?\s*\(|yaml\.load\s*\((?![^)]*Loader)")),
    ("raw-html", "low", "raw HTML rendering",
     re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*=|\|\s*safe\b")),
    ("weak-hash", "low", "weak hash function",
     re.compile(r"(?i)\b(?:md5|sha1)\s*\(")),
]
PLACEHOLDER = re.compile(r"(?i)example|changeme|placeholder|dummy|xxxx|<[^>]+>|\$\{|os\.environ|process\.env")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def redact(line: str) -> str:
    """Hide the value of anything that looks like a quoted secret."""
    return re.sub(r"""(["'])([^"'\s]{4})[^"'\s]{2,}\1""", r"\1\2...\1", line.strip())[:120]


def scan(diff_text: str) -> list[dict]:
    findings = []
    path, line_number = None, 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else re.sub(r"^b/", "", target)
            continue
        if raw.startswith("--- "):
            continue
        hunk = HUNK.match(raw)
        if hunk:
            line_number = int(hunk.group(1)) - 1
            continue
        if path is None or raw.startswith("-") or raw.startswith("\\"):
            continue
        line_number += 1
        if not raw.startswith("+"):
            continue
        added = raw[1:]
        for rule, severity, description, pattern in RULES:
            if not pattern.search(added):
                continue
            if rule == "hardcoded-secret" and PLACEHOLDER.search(added):
                continue
            findings.append({
                "rule": rule, "severity": severity, "description": description,
                "path": path, "line": line_number, "code": redact(added),
            })
    return sorted(findings, key=lambda f: (SEVERITY_ORDER[f["severity"]], f["path"], f["line"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("diff", nargs="?", help="unified diff file (default: stdin)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if args.diff:
        with open(args.diff, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()

    findings = scan(text)
    if args.format == "json":
        print(json.dumps(findings, indent=2))
    elif not findings:
        print("No findings on added lines.")
    else:
        for finding in findings:
            print(f"{finding['severity'].upper():<6} {finding['path']}:{finding['line']}  "
                  f"{finding['description']} [{finding['rule']}]")
            print(f"       {finding['code']}")
        counts = {level: sum(f["severity"] == level for f in findings) for level in SEVERITY_ORDER}
        print(f"\n{len(findings)} finding(s): " + ", ".join(f"{n} {level}" for level, n in counts.items()))
    return 1 if any(f["severity"] == "high" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
