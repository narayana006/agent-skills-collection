import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def load_script(relative: str):
    """Import a skill script by path (skill folders are not Python packages)."""
    path = REPO / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def make_skill(tmp_path):
    """Create a skill folder under tmp_path/skills and return its path."""

    def _make(name="demo-skill", frontmatter=None, body="# Demo\n\nDo the thing.\n", files=None):
        if frontmatter is None:
            frontmatter = (
                f"name: {name}\n"
                "description: Summarise a log file into its ten most common errors. "
                "Use when the user asks what is going wrong in a log."
            )
        skill = tmp_path / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
        for relative, content in (files or {}).items():
            target = skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return skill

    return _make
