"""Parse the YAML frontmatter block at the top of a SKILL.md file.

Only the subset skills actually use is supported, so no YAML dependency is
needed: top-level ``key: value`` pairs, single or double quoted strings,
block scalars (``>`` folded, ``|`` literal) and plain multi-line values
continued on indented lines. Nested mappings and lists are kept as raw text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?$")


class FrontmatterError(ValueError):
    """The frontmatter block is missing or malformed. ``line`` is 1-based."""

    def __init__(self, message: str, line: int = 1):
        super().__init__(message)
        self.line = line


@dataclass
class Document:
    fields: dict[str, str] = field(default_factory=dict)
    field_lines: dict[str, int] = field(default_factory=dict)
    body: str = ""
    body_start: int = 1  # 1-based line number of the first body line


def _unquote(value: str, line: int) -> str:
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            raise FrontmatterError(f"unterminated {quote} quoted string", line)
        inner = value[1:-1]
        if quote == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    # Strip a trailing YAML comment from a plain scalar.
    return re.sub(r"\s+#.*$", "", value)


def _fold(lines: list[str], style: str) -> str:
    stripped = [line.strip() for line in lines]
    if style == "|":
        return "\n".join(stripped).strip()
    paragraphs, current = [], []
    for line in stripped:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n".join(paragraphs)


def parse(text: str) -> Document:
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file must start with a '---' frontmatter line", 1)
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter is not closed by a '---' line", 1) from None

    doc = Document(body="\n".join(lines[end + 1 :]), body_start=end + 2)
    i = 1
    while i < end:
        raw, number = lines[i], i + 1
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in " \t":
            raise FrontmatterError("unexpected indented line in frontmatter", number)
        match = _KEY.match(raw)
        if not match:
            raise FrontmatterError(f"expected 'key: value', got: {raw.strip()!r}", number)
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in doc.fields:
            raise FrontmatterError(f"duplicate key '{key}'", number)

        # Gather indented continuation lines belonging to this key.
        block: list[str] = []
        while i < end and (not lines[i].strip() or lines[i][0] in " \t"):
            block.append(lines[i])
            i += 1

        if value[:1] in (">", "|") and value.rstrip("+-") in (">", "|"):
            doc.fields[key] = _fold(block, value[0])
        elif value[:1] in ("'", '"'):
            doc.fields[key] = _unquote(value, number)
        elif value and block and any(line.strip() for line in block):
            doc.fields[key] = _fold([value, *block], ">")
        elif value:
            doc.fields[key] = _unquote(value, number)
        else:
            # Nested mapping or list: keep the raw text so callers can see it is set.
            doc.fields[key] = "\n".join(line.rstrip() for line in block).strip("\n")
        doc.field_lines[key] = number
    return doc
