import shutil

import pytest

from skill_lint.checks import find_skills, lint_skill


def rules(skill):
    return [issue.rule for issue in lint_skill(skill, skill.parent)]


def test_valid_skill_has_no_issues(make_skill):
    skill = make_skill(
        body="# Demo\n\nRun `scripts/run.py`, then read [the notes](notes.md#usage).\n",
        files={"scripts/run.py": "print('ok')\n", "notes.md": "# Notes\n\n## Usage\n"},
    )
    assert lint_skill(skill, skill.parent) == []


def test_folder_without_skill_file(tmp_path):
    (tmp_path / "skills" / "empty").mkdir(parents=True)
    assert rules(tmp_path / "skills" / "empty") == ["missing-skill-file"]


def test_missing_frontmatter_is_reported_with_path_and_line(make_skill):
    skill = make_skill()
    (skill / "SKILL.md").write_text("# Just a heading\n")
    (issue,) = lint_skill(skill, skill.parent)
    assert (issue.rule, issue.level, issue.path, issue.line) == ("frontmatter", "error", "demo-skill/SKILL.md", 1)


@pytest.mark.parametrize("name", ["Demo", "demo_skill", "-demo", "demo-", "demo--skill", "démo"])
def test_name_format_violations(make_skill, name):
    skill = make_skill(frontmatter=f"name: {name}\ndescription: Does one specific thing. Use when the user asks for it.")
    assert "name-format" in rules(skill)


def test_name_must_match_folder_and_stay_within_limit(make_skill):
    long_name = "a" * 65
    assert rules(make_skill("one", frontmatter="name: two\ndescription: Does one specific thing. Use when the user asks.")) == ["name-mismatch"]
    assert "name-length" in rules(
        make_skill(long_name, frontmatter=f"name: {long_name}\ndescription: Does one specific thing. Use when the user asks.")
    )


def test_missing_name_and_description(make_skill):
    assert rules(make_skill(frontmatter="license: MIT")) == ["name-missing", "description-missing"]


def test_description_limits(make_skill):
    assert rules(make_skill("short", frontmatter="name: short\ndescription: Helps with logs.")) == ["description-short"]
    too_long = "word " * 250
    assert rules(make_skill("long", frontmatter=f"name: long\ndescription: {too_long}")) == ["description-length"]
    assert "description-markup" in rules(
        make_skill("tags", frontmatter="name: tags\ndescription: Use <b>when</b> the user asks about logs and errors in them.")
    )


def test_empty_and_overlong_body(make_skill):
    assert rules(make_skill("empty", body="\n")) == ["body-empty"]
    issues = lint_skill(skill := make_skill("big", body="line\n" * 501), skill.parent)
    assert [(i.rule, i.level) for i in issues] == [("body-long", "warning")]


def test_broken_absolute_and_escaping_links(make_skill, tmp_path):
    (tmp_path / "skills" / "README.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "skills" / "README.md").write_text("outside")
    skill = make_skill(
        body=(
            "See [missing](missing.md), [abs](/etc/hosts) and [outside](../README.md).\n"
            "External [site](https://example.com), [mail](mailto:a@example.com) and [anchor](#top) are fine.\n"
            "![diagram](images/flow.png)\n"
        )
    )
    issues = lint_skill(skill, skill.parent)
    assert [(i.rule, i.line) for i in issues] == [
        ("link-broken", 6), ("link-absolute", 6), ("link-outside-skill", 6), ("link-broken", 8),
    ]


def test_links_in_other_markdown_files_are_checked(make_skill):
    skill = make_skill(body="Read [the reference](docs/reference.md).\n", files={"docs/reference.md": "[back](../SKILL.md) [gone](gone.md)\n"})
    (issue,) = lint_skill(skill, skill.parent)
    assert (issue.rule, issue.path) == ("link-broken", "demo-skill/docs/reference.md")


def test_links_and_paths_inside_code_fences_are_ignored(make_skill):
    skill = make_skill(body="```markdown\n[example](nowhere.md)\nrun `scripts/nothing.py`\n```\n\nReal text.\n")
    assert rules(skill) == []


def test_mentioned_script_must_exist(make_skill):
    skill = make_skill(
        body="Run `python3 scripts/build.py --all` and `scripts/missing.sh`. Globs like `scripts/*.py` are skipped.\n",
        files={"scripts/build.py": "x = 1\n"},
    )
    issues = lint_skill(skill, skill.parent)
    assert [(i.rule, i.message.split("'")[1]) for i in issues] == [("file-reference-broken", "scripts/missing.sh")]


def test_python_and_json_syntax_errors(make_skill):
    skill = make_skill(files={"scripts/bad.py": "def broken(:\n    pass\n", "assets/config.json": '{"a": 1,}\n'})
    issues = {issue.path: issue for issue in lint_skill(skill, skill.parent)}
    assert issues["demo-skill/scripts/bad.py"].rule == "script-syntax"
    assert issues["demo-skill/scripts/bad.py"].line == 1
    assert "invalid JSON" in issues["demo-skill/assets/config.json"].message


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_shell_syntax_error_and_missing_executable_bit(make_skill):
    skill = make_skill(files={"scripts/run.sh": "#!/bin/sh\nif true; then\n  echo hi\n", "scripts/ok.sh": "echo fine\n"})
    issues = lint_skill(skill, skill.parent)
    assert [(i.rule, i.level, i.path) for i in issues] == [
        ("script-syntax", "error", "demo-skill/scripts/run.sh"),
        ("script-not-executable", "warning", "demo-skill/scripts/run.sh"),
    ]
    (skill / "scripts" / "run.sh").write_text("#!/bin/sh\necho hi\n")
    (skill / "scripts" / "run.sh").chmod(0o755)
    assert lint_skill(skill, skill.parent) == []


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_javascript_syntax_error(make_skill):
    skill = make_skill(files={"scripts/bad.mjs": "const = 5;\n", "scripts/good.js": "console.log(1);\n"})
    issues = lint_skill(skill, skill.parent)
    assert [(i.rule, i.path) for i in issues] == [("script-syntax", "demo-skill/scripts/bad.mjs")]


def test_find_skills_accepts_a_collection_or_a_single_skill(make_skill, tmp_path):
    first, second = make_skill("alpha"), make_skill("beta")
    (tmp_path / "skills" / ".hidden").mkdir()
    assert find_skills(tmp_path / "skills") == [first, second]
    assert find_skills(first) == [first]
