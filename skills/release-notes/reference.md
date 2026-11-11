# Commit grouping reference

`scripts/collect_commits.py` reads `git log` for the range and assigns each commit to a section.

| Subject starts with | Section |
| --- | --- |
| `feat:` / `feature:` | Added |
| `fix:` / `bugfix:` | Fixed |
| `perf:` | Performance |
| `docs:` | Documentation |
| `refactor:`, `test:`, `tests:`, `build:`, `ci:`, `chore:`, `style:` | Internal |
| anything else | Other |

A scope in parentheses is kept as a prefix: `fix(api): reject empty ids` becomes
`**api:** reject empty ids`.

A commit is also listed under **Breaking changes** when its type is followed by `!`
(`feat!: drop v1 endpoints`) or its body contains a line starting with `BREAKING CHANGE:`.

Merge commits are skipped. Commits that do not follow the convention land in "Other"; read those
by hand, they are often the most important ones.
