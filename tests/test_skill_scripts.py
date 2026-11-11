"""Tests for the helper scripts bundled with the skills."""

import subprocess
import sys

import pytest
from conftest import REPO, load_script

collect_commits = load_script("skills/release-notes/scripts/collect_commits.py")
usage_report = load_script("skills/dependency-migration/scripts/usage_report.py")
scan_diff = load_script("skills/security-pre-merge/scripts/scan_diff.py")
audit_html = load_script("skills/seo-audit/scripts/audit_html.py")


# --- release-notes ----------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path):
    def git(*args):
        subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@example.com",
             "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
            check=True, capture_output=True,
        )

    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "chore: initial commit")
    git("tag", "v1.0.0")
    for message in [
        "feat(api): add bulk export endpoint (#12)",
        "fix: stop exports timing out on large projects",
        "feat!: drop the v1 endpoints",
        "refactor: split export job\n\nBREAKING CHANGE: EXPORT_DIR is now required",
        "Update the logo",
    ]:
        git("commit", "-q", "--allow-empty", "-m", message)
    return tmp_path


def test_classify_commit_subjects():
    assert collect_commits.classify("fix(ui): align buttons", "") == {
        "section": "Fixed", "text": "**ui:** align buttons", "breaking": False,
    }
    assert collect_commits.classify("feat!: new config format", "")["breaking"] is True
    assert collect_commits.classify("Merge the things", "")["section"] == "Other"
    assert collect_commits.classify("note: not a known type", "")["section"] == "Other"


def test_collects_and_groups_commits_since_latest_tag(git_repo):
    start = collect_commits.latest_tag(str(git_repo))
    assert start == "v1.0.0"
    sections = collect_commits.group(collect_commits.collect(str(git_repo), start, "HEAD"))
    assert list(sections) == ["Breaking changes", "Added", "Fixed", "Internal", "Other"]
    assert [c["text"] for c in sections["Added"]] == ["drop the v1 endpoints", "**api:** add bulk export endpoint (#12)"]
    assert len(sections["Breaking changes"]) == 2
    assert all(c["subject"] != "chore: initial commit" for group in sections.values() for c in group)


def test_markdown_output_from_the_command_line(git_repo, capsys):
    assert collect_commits.main(["--repo", str(git_repo)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Changes v1.0.0..HEAD\n\n## Breaking changes\n")
    assert "## Fixed\n- stop exports timing out on large projects (" in out


def test_repository_without_tags_uses_full_history(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    assert collect_commits.latest_tag(str(tmp_path)) is None


# --- dependency-migration ---------------------------------------------------

def test_usage_report_on_python_example():
    files = usage_report.scan("requests", str(REPO / "examples" / "legacy-app"))
    assert [(f["path"], len(f["uses"])) for f in files] == [("src/client.py", 3), ("src/health.py", 1)]
    assert files[0]["uses"][2]["names"] == ["ConnectionError", "Timeout"]


def test_usage_report_on_javascript_and_typescript(tmp_path):
    (tmp_path / "node_modules" / "moment").mkdir(parents=True)
    (tmp_path / "node_modules" / "moment" / "index.js").write_text("require('moment')\n")
    (tmp_path / "a.ts").write_text(
        "import moment from 'moment';\nimport { duration, type Moment } from \"moment\";\n"
        "import 'moment/locale/de';\nimport momentum from 'momentum';\n"
    )
    (tmp_path / "b.js").write_text("const m = require('moment');\nconst lazy = () => import('moment');\n")
    files = usage_report.scan("moment", str(tmp_path))
    assert [(f["path"], [u["line"] for u in f["uses"]]) for f in files] == [("a.ts", [1, 2, 3]), ("b.js", [1, 2])]
    assert files[0]["uses"][1]["names"] == ["duration", "Moment"]


def test_usage_report_does_not_match_longer_package_names(tmp_path):
    (tmp_path / "a.py").write_text("import requests_mock\nfrom requestsx import y\nimport os\n")
    assert usage_report.scan("requests", str(tmp_path)) == []


# --- security-pre-merge -----------------------------------------------------

def diff_for(path, *added):
    body = "\n".join(f"+{line}" for line in added)
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,{len(added)} @@\n{body}\n"


def test_scan_example_diff_finds_each_planted_problem():
    findings = scan_diff.scan((REPO / "examples" / "change.diff").read_text())
    assert [(f["rule"], f["path"], f["line"]) for f in findings] == [
        ("tls-verify-off", "app/reports.py", 22),
        ("hardcoded-secret", "app/settings.py", 12),
        ("sql-string-building", "app/reports.py", 27),
        ("shell-injection", "app/reports.py", 31),
        ("raw-html", "web/components/Comment.jsx", 5),
    ]


def test_secret_values_are_redacted_in_output():
    (finding,) = scan_diff.scan(diff_for("config.py", 'API_KEY = "zq81-abcdefgh12345678"'))
    assert finding["rule"] == "hardcoded-secret"
    assert "abcdefgh" not in finding["code"]
    assert '"zq81..."' in finding["code"]


def test_key_patterns_are_detected():
    access_key = "AKIA" + "Q" * 16  # assembled here so no key-shaped literal is committed
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    findings = scan_diff.scan(diff_for("deploy.sh", f"export KEY_ID={access_key}", header))
    assert [f["rule"] for f in findings] == ["aws-access-key", "private-key"]


def test_placeholders_environment_reads_and_removed_lines_are_ignored():
    text = diff_for(
        "settings.py",
        'password = "changeme-example"',
        'token = os.environ["AUTH_TOKEN"]',
        "model.eval()",
    ) + '-password = "an-old-real-looking-one"\n'
    assert scan_diff.scan(text) == []


def test_exit_status_reflects_high_severity(tmp_path, capsys):
    low = tmp_path / "low.diff"
    low.write_text(diff_for("a.py", "digest = md5(data)"))
    assert scan_diff.main([str(low)]) == 0
    assert scan_diff.main([str(REPO / "examples" / "change.diff")]) == 1
    assert "5 finding(s): 2 high, 2 medium, 1 low" in capsys.readouterr().out


# --- seo-audit --------------------------------------------------------------

def test_audit_example_site():
    pages = {page["path"]: [p["rule"] for p in page["problems"]] for page in audit_html.audit(str(REPO / "examples" / "site"))}
    assert pages["index.html"] == ["title-duplicate"]
    assert pages["menu.html"] == ["title-missing", "description-missing", "h1-missing"]
    assert pages["about.html"] == [
        "description-length", "h1-multiple", "img-alt-missing", "lang-missing",
        "viewport-missing", "canonical-missing", "noindex", "title-duplicate",
    ]


def test_clean_page_and_length_rules():
    good = (
        '<html lang="en"><head><title>Short title</title>'
        '<meta name="description" content="' + "A clear summary of the page. " * 3 + '">'
        '<meta name="viewport" content="width=device-width"><link rel="canonical" href="https://example.com/">'
        '</head><body><h1>Hi</h1><img src="a.png" alt=""></body></html>'
    )
    assert audit_html.audit_page(good)[1] == []
    long_title = good.replace("Short title", "T" * 61)
    assert [p["rule"] for p in audit_html.audit_page(long_title)[1]] == ["title-length"]


def test_image_without_alt_reports_its_line():
    _, problems = audit_html.audit_page("<html lang='en'>\n<body>\n<h1>x</h1>\n<img src='a.png'>\n</body></html>")
    assert {"level": "error", "rule": "img-alt-missing", "message": "<img> has no alt attribute", "line": 4} in problems


def test_command_line_exit_codes(tmp_path, capsys):
    assert audit_html.main([str(REPO / "examples" / "site")]) == 1
    assert "3 page(s) checked: 4 error(s), 8 warning(s)" in capsys.readouterr().out
    assert audit_html.main([str(tmp_path)]) == 2
    assert audit_html.main([str(REPO / "examples" / "site" / "index.html")]) == 0


def test_scripts_run_standalone_with_only_the_standard_library():
    for script in sorted((REPO / "skills").glob("*/scripts/*.py")):
        result = subprocess.run([sys.executable, "-I", str(script), "--help"], capture_output=True, text=True)
        assert result.returncode == 0, f"{script}: {result.stderr}"
        assert "usage:" in result.stdout.lower()
