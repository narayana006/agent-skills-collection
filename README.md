# agent-skills-collection

Reusable, tool-agnostic agent skills (a `SKILL.md` plus helper scripts per folder) and `skill-lint`, a validator that keeps them well-formed.

**Status: first working version.** Five skills ship today (release notes, dependency migration, security pre-merge review, SEO audit, skill authoring), each with tested helper scripts where a step needs to be exact, plus the `skill-lint` CLI that CI runs on every push. The iOS App Store pre-submit audit from the original plan is not written yet.

## What a skill is

A skill is a folder. `SKILL.md` starts with a small frontmatter block (`name` and `description`) followed by instructions; scripts and reference files sit next to it. An agent that loads skill folders reads the description to decide when the skill applies, then follows the instructions and runs the scripts. Nothing here depends on a particular agent product: the instructions are Markdown and the scripts need only a stock `python3`.

```text
skills/release-notes/
├── SKILL.md                    # frontmatter + the workflow
├── reference.md                # detail the workflow links to
└── scripts/collect_commits.py  # the exact, repeatable part
```

## The skills

| Skill | Use it when | Bundled script |
| --- | --- | --- |
| [release-notes](skills/release-notes/SKILL.md) | you need release notes or a changelog entry from a commit range | `collect_commits.py` groups commits by conventional-commit type, breaking changes first |
| [dependency-migration](skills/dependency-migration/SKILL.md) | upgrading a major version or replacing a library | `usage_report.py` lists every import of a package in Python, JS and TS files |
| [security-pre-merge](skills/security-pre-merge/SKILL.md) | reviewing a branch before merge | `scan_diff.py` flags likely secrets and risky constructs on added lines; a [checklist](skills/security-pre-merge/checklist.md) covers the rest |
| [seo-audit](skills/seo-audit/SKILL.md) | auditing a static site or built Next.js output | `audit_html.py` checks titles, descriptions, headings, alt text, canonical links |
| [skill-authoring](skills/skill-authoring/SKILL.md) | writing a new skill or fixing one | a [template](skills/skill-authoring/template.md) to copy |

## Install a skill

Copy the folder into the directory your agent loads skills from:

```bash
git clone https://github.com/narayana006/agent-skills-collection
cp -r agent-skills-collection/skills/release-notes <your-agent-skills-dir>/
```

Each folder is self-contained, so copy only the ones you want. If your agent has no skills directory, point it at the `SKILL.md` file or paste its contents into the conversation; the scripts run from the skill folder either way.

## Try the scripts

The scripts work on their own, which is also the quickest way to see what a skill gives the agent. From a clone of this repository:

```console
$ python3 skills/seo-audit/scripts/audit_html.py examples/site
about.html:1: warning: meta description is 9 characters (aim for 50 to 160) [description-length]
about.html:1: warning: page has 2 <h1> elements [h1-multiple]
about.html:12: error: <img> has no alt attribute [img-alt-missing]
about.html:1: warning: <html> has no lang attribute [lang-missing]
about.html:1: warning: no viewport meta tag [viewport-missing]
about.html:1: warning: no canonical link [canonical-missing]
about.html:1: warning: robots meta tag contains noindex [noindex]
about.html:1: warning: same title as index.html [title-duplicate]
index.html:1: warning: same title as about.html [title-duplicate]
menu.html:1: error: page has no <title> [title-missing]
menu.html:1: error: page has no meta description [description-missing]
menu.html:1: error: page has no <h1> [h1-missing]

3 page(s) checked: 4 error(s), 8 warning(s)
```

```console
$ python3 skills/security-pre-merge/scripts/scan_diff.py examples/change.diff
HIGH   app/reports.py:22  TLS certificate verification disabled [tls-verify-off]
       response = requests.get(url, timeout=10, verify=False)
HIGH   app/settings.py:12  hard-coded credential [hardcoded-secret]
       DATABASE_PASSWORD = "tr0u..."
MEDIUM app/reports.py:27  SQL built with string formatting [sql-string-building]
       return db.execute("SELECT * FROM orders WHERE customer = '%s'" % customer_name)
MEDIUM app/reports.py:31  shell command built at run time [shell-injection]
       subprocess.run("tar czf /tmp/export.tgz " + path, shell=True)
LOW    web/components/Comment.jsx:5  raw HTML rendering [raw-html]
       <p dangerouslySetInnerHTML={{ __html: comment.body }} />

5 finding(s): 2 high, 2 medium, 1 low
```

```console
$ python3 skills/dependency-migration/scripts/usage_report.py requests examples/legacy-app
requests: 4 import(s) in 2 file(s)

src/client.py (3)
     1: import requests
     2: from requests.adapters import HTTPAdapter
     3: from requests.exceptions import ConnectionError, Timeout

src/health.py (1)
     1: import requests

Imported names: ConnectionError x1, HTTPAdapter x1, Timeout x1
```

`collect_commits.py` needs a git repository. In one whose history after tag `v1.0.0` is four conventional commits, `python3 skills/release-notes/scripts/collect_commits.py` prints:

```text
# Changes v1.0.0..HEAD

## Breaking changes
- drop the v1 endpoints (8c12037)

## Added
- drop the v1 endpoints (8c12037)
- **api:** add bulk export endpoint (#12) (3bf3254)

## Fixed
- stop exports timing out on large projects (8d8bd90)

## Documentation
- describe the export format (3052859)
```

The audit and scan scripts exit with status 1 when they find errors or high-severity findings, so they can also gate a CI job. All four accept `--format json`.

## skill-lint

A validator for skill folders, yours as well as the ones here. Python 3.10+, no dependencies.

```bash
pip install git+https://github.com/narayana006/agent-skills-collection
skill-lint path/to/skills        # a folder of skills, or a single skill folder
```

On this repository's skills:

```console
$ skill-lint skills
ok    dependency-migration
ok    release-notes
ok    security-pre-merge
ok    seo-audit
ok    skill-authoring

5 skill(s) checked: 0 error(s), 0 warning(s)
```

On the deliberately broken example:

```console
$ skill-lint examples/broken-skills
FAIL  Release_Notes
      Release_Notes/SKILL.md:2: error: name 'Release_Notes' must be lowercase letters, digits and single hyphens, with no hyphen at either end [name-format]
      Release_Notes/SKILL.md:3: warning: description is very short; say what the skill does and when to use it [description-short]
      Release_Notes/SKILL.md:8: error: link target 'docs/style.md' does not exist [link-broken]
      Release_Notes/SKILL.md:8: error: 'scripts/collect.py' is mentioned but does not exist in the skill [file-reference-broken]
      Release_Notes/SKILL.md:9: error: link '../../../HANDBOOK.md' points outside the skill folder, so it breaks when the skill is copied [link-outside-skill]
      Release_Notes/scripts/check.sh:4: error: shell: syntax error: unexpected end of file [script-syntax]
      Release_Notes/scripts/check.sh:1: warning: file has a shebang but is not executable (chmod +x) [script-not-executable]

1 skill(s) checked: 5 error(s), 2 warning(s)
```

Options: `--strict` makes warnings fail too, `--format json` prints a machine-readable report, and with no path it checks `./skills`. Exit status is 0 when clean, 1 when there are errors, 2 for a bad path.

### What it checks

| Area | Rules |
| --- | --- |
| Frontmatter | `SKILL.md` exists, opens with a `---` block that closes, keys are well-formed and not duplicated (`missing-skill-file`, `frontmatter`) |
| Name | present, at most 64 characters, lowercase letters, digits and single hyphens, equal to the folder name (`name-missing`, `name-length`, `name-format`, `name-mismatch`) |
| Description | present, at most 1024 characters, no XML or HTML tags; warns under 8 words (`description-missing`, `description-length`, `description-markup`, `description-short`) |
| Body | not empty; warns over 500 lines (`body-empty`, `body-long`) |
| Links | every relative Markdown link and image in every `.md` file of the skill resolves, is not absolute and stays inside the skill folder (`link-broken`, `link-absolute`, `link-outside-skill`) |
| File mentions | paths such as `scripts/run.py` written in inline code exist (`file-reference-broken`) |
| Scripts | `.py` parses, `.json` loads, `.sh`/`.bash` pass `bash -n`, `.js`/`.mjs`/`.cjs` pass `node --check`; warns when a file with a shebang is not executable (`script-syntax`, `script-not-executable`, `script-unchecked`) |

Links and paths inside fenced code blocks are ignored, as are external URLs and `#anchor` links.

### In CI

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install git+https://github.com/narayana006/agent-skills-collection
- run: skill-lint skills --strict
```

## Feature checklist

- [x] Release-notes writer from git history
- [x] Dependency / framework migration helper
- [x] Security pre-merge checklist
- [x] SEO audit for static and Next.js sites
- [x] Template and guide for writing your own skill
- [x] `skill-lint` validator, tests and CI
- [ ] iOS App Store pre-submit audit (common rejection reasons)

## Limitations

- The helper scripts are pattern-based. `scan_diff.py` looks at one added line at a time and knows nothing about data flow; `audit_html.py` reads files and does not run JavaScript or fetch URLs; `usage_report.py` finds import statements, not every use of an imported name. Each skill tells the agent what the script cannot see.
- `collect_commits.py` only understands conventional-commit subjects; everything else lands under "Other".
- `skill-lint` reads frontmatter with a small built-in parser: top-level keys, quoted strings and block scalars. Nested values are accepted but not validated. It does not check that link `#anchors` exist or that external URLs are alive.
- Shell and JavaScript syntax checks need `bash` and `node` on the PATH; without them the file gets a `script-unchecked` warning.
- How well an agent follows a skill depends on the agent. The skills have been validated structurally and their scripts are tested; they have not been benchmarked across agents.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: start from the skill-authoring template, keep skills self-contained and tool-agnostic, and make sure `skill-lint skills --strict` and `pytest` pass.

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
