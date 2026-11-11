import json

from conftest import REPO

from skill_lint.cli import main


def test_every_skill_in_this_repository_passes_strict(capsys):
    assert main([str(REPO / "skills"), "--strict"]) == 0
    out = capsys.readouterr().out
    assert "0 error(s), 0 warning(s)" in out
    for name in ("release-notes", "dependency-migration", "security-pre-merge", "seo-audit", "skill-authoring"):
        assert f"ok    {name}" in out


def test_broken_example_fails_with_every_expected_rule(capsys):
    assert main([str(REPO / "examples" / "broken-skills"), "--format", "json"]) == 1
    report = json.loads(capsys.readouterr().out)
    found = {issue["rule"] for issue in report["skills"][0]["issues"]}
    assert {"name-format", "description-short", "link-broken", "link-outside-skill", "file-reference-broken"} <= found
    assert report["skills"][0]["ok"] is False
    assert report["errors"] >= 4


def test_warnings_fail_only_in_strict_mode(make_skill, capsys):
    skill = make_skill("terse", frontmatter="name: terse\ndescription: Helps with logs.")
    assert main([str(skill.parent)]) == 0
    assert "warning: description is very short" in capsys.readouterr().out
    assert main([str(skill.parent), "--strict"]) == 1


def test_single_skill_folder_and_multiple_paths(make_skill, capsys):
    first, second = make_skill("alpha"), make_skill("beta")
    assert main([str(first), str(second)]) == 0
    assert "2 skill(s) checked" in capsys.readouterr().out


def test_missing_or_empty_directory_is_a_usage_error(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2
    assert main([str(tmp_path)]) == 2
    assert "no skill folders found" in capsys.readouterr().err
