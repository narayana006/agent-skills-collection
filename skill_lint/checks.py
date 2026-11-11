"""The lint rules. Each check yields Issue objects for one skill folder."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

from skill_lint.frontmatter import Document, FrontmatterError, parse

SKILL_FILE = "SKILL.md"
NAME_MAX = 64
DESCRIPTION_MAX = 1024
DESCRIPTION_MIN_WORDS = 8
BODY_MAX_LINES = 500

_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_SCRIPT_REF = re.compile(r"(?<![\w./-])((?:scripts|references|assets)/[\w./-]*\w)")


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    rule: str
    path: str  # relative to the directory the linter was pointed at
    line: int
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def find_skills(root: Path) -> list[Path]:
    """Skill folders under ``root``. ``root`` itself may be a single skill."""
    if (root / SKILL_FILE).is_file():
        return [root]
    return sorted(
        child for child in root.iterdir() if child.is_dir() and not child.name.startswith(".")
    )


def lint_skill(skill: Path, base: Path) -> list[Issue]:
    def rel(path: Path) -> str:
        return os.path.relpath(path, base)

    skill_md = skill / SKILL_FILE
    if not skill_md.is_file():
        return [Issue("error", "missing-skill-file", rel(skill), 1, f"folder has no {SKILL_FILE}")]

    issues: list[Issue] = []
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    try:
        doc = parse(text)
    except FrontmatterError as error:
        issues.append(Issue("error", "frontmatter", rel(skill_md), error.line, str(error)))
    else:
        issues.extend(_check_frontmatter(doc, skill, rel(skill_md)))
        issues.extend(_check_body(doc, rel(skill_md)))

    for markdown in sorted(skill.rglob("*.md")):
        issues.extend(_check_references(markdown, skill, rel(markdown)))
    for path in sorted(p for p in skill.rglob("*") if p.is_file()):
        issues.extend(_check_script(path, rel(path)))
    return issues


def _check_frontmatter(doc: Document, skill: Path, path: str) -> Iterator[Issue]:
    name = doc.fields.get("name", "")
    line = doc.field_lines.get("name", 1)
    if not name:
        yield Issue("error", "name-missing", path, line, "frontmatter needs a non-empty 'name'")
    else:
        if len(name) > NAME_MAX:
            yield Issue("error", "name-length", path, line, f"name is {len(name)} characters; the limit is {NAME_MAX}")
        if not _NAME.match(name):
            yield Issue(
                "error", "name-format", path, line,
                f"name '{name}' must be lowercase letters, digits and single hyphens, "
                "with no hyphen at either end",
            )
        elif name != skill.name:
            yield Issue("error", "name-mismatch", path, line, f"name '{name}' does not match folder name '{skill.name}'")

    description = doc.fields.get("description", "")
    line = doc.field_lines.get("description", 1)
    if not description.strip():
        yield Issue("error", "description-missing", path, line, "frontmatter needs a non-empty 'description'")
        return
    if len(description) > DESCRIPTION_MAX:
        yield Issue(
            "error", "description-length", path, line,
            f"description is {len(description)} characters; the limit is {DESCRIPTION_MAX}",
        )
    if "<" in description and re.search(r"<[A-Za-z/][^>]*>", description):
        yield Issue("error", "description-markup", path, line, "description must be plain text, without XML or HTML tags")
    if len(description.split()) < DESCRIPTION_MIN_WORDS:
        yield Issue(
            "warning", "description-short", path, line,
            "description is very short; say what the skill does and when to use it",
        )


def _check_body(doc: Document, path: str) -> Iterator[Issue]:
    body_lines = doc.body.splitlines()
    if not doc.body.strip():
        yield Issue("error", "body-empty", path, doc.body_start, "SKILL.md has no instructions after the frontmatter")
    elif len(body_lines) > BODY_MAX_LINES:
        yield Issue(
            "warning", "body-long", path, doc.body_start,
            f"body is {len(body_lines)} lines; move detail into separate files and link to them "
            f"(suggested limit {BODY_MAX_LINES})",
        )


def _check_references(markdown: Path, skill: Path, path: str) -> Iterator[Issue]:
    """Relative Markdown links and `scripts/...` mentions must resolve inside the skill."""
    in_fence = False
    skill_root = skill.resolve()
    lines = markdown.read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in _LINK.finditer(_INLINE_CODE.sub("", line)):
            target = match.group(1)
            if target.startswith("#") or _SCHEME.match(target) or target.startswith("//"):
                continue
            file_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not file_part:
                continue
            if file_part.startswith("/"):
                yield Issue("error", "link-absolute", path, number, f"link '{target}' is absolute; use a path relative to this file")
                continue
            resolved = (markdown.parent / file_part).resolve()
            if not resolved.is_relative_to(skill_root):
                yield Issue(
                    "error", "link-outside-skill", path, number,
                    f"link '{target}' points outside the skill folder, so it breaks when the skill is copied",
                )
            elif not resolved.exists():
                yield Issue("error", "link-broken", path, number, f"link target '{target}' does not exist")

        # Paths like `scripts/run.py` are how instructions point an agent at bundled files.
        for code in _INLINE_CODE.findall(line):
            for ref in _SCRIPT_REF.findall(code):
                if any(ch in ref for ch in "*<>{}$"):
                    continue
                if not (skill / ref).exists():
                    yield Issue("error", "file-reference-broken", path, number, f"'{ref}' is mentioned but does not exist in the skill")


def _run_syntax_check(command: list[str]) -> tuple[int, str] | None:
    """Return (line, message) for a syntax error, or None when the syntax is fine."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return None
    output = (result.stderr or result.stdout).strip().splitlines()
    for line in output:
        # bash: "file: line 4: syntax error: ..."   node: "file:4" then "SyntaxError: ..."
        if match := re.search(r"line (\d+): (.+)$", line):
            return int(match.group(1)), match.group(2)
    line_number = next((int(m.group(1)) for m in [re.search(r":(\d+)$", output[0])] if m), 1) if output else 1
    message = next((line for line in output if "Error" in line), output[0] if output else "")
    return line_number, message or f"exit status {result.returncode}"


def _check_script(file: Path, path: str) -> Iterator[Issue]:
    suffix = file.suffix.lower()
    try:
        source = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return  # binary asset
    first_line = source.split("\n", 1)[0]

    if suffix == ".py":
        try:
            ast.parse(source, filename=str(file))
        except SyntaxError as error:
            yield Issue("error", "script-syntax", path, error.lineno or 1, f"Python syntax error: {error.msg}")
    elif suffix == ".json":
        try:
            json.loads(source)
        except json.JSONDecodeError as error:
            yield Issue("error", "script-syntax", path, error.lineno, f"invalid JSON: {error.msg}")
    elif suffix in (".sh", ".bash") or (not suffix and re.match(r"#!.*\b(ba)?sh\b", first_line)):
        shell = shutil.which("bash") or shutil.which("sh")
        if shell is None:
            yield Issue("warning", "script-unchecked", path, 1, "no shell found; syntax not checked")
        elif failure := _run_syntax_check([shell, "-n", str(file)]):
            yield Issue("error", "script-syntax", path, failure[0], f"shell: {failure[1]}")
    elif suffix in (".js", ".mjs", ".cjs"):
        node = shutil.which("node")
        if node is None:
            yield Issue("warning", "script-unchecked", path, 1, "node not found; syntax not checked")
        elif failure := _run_syntax_check([node, "--check", str(file)]):
            yield Issue("error", "script-syntax", path, failure[0], f"JavaScript: {failure[1]}")
    else:
        return

    if first_line.startswith("#!") and os.name == "posix" and not os.access(file, os.X_OK):
        yield Issue("warning", "script-not-executable", path, 1, "file has a shebang but is not executable (chmod +x)")
