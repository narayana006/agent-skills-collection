---
name: release-notes
description: Write release notes or a changelog entry from git history. Use when the user asks for release notes, a changelog, "what changed since the last release", or a summary of commits between two tags or branches.
---

# Release notes from git history

Turn a range of commits into notes a user of the project can read in a minute.

## Steps

1. **Pick the range.** If the user named two refs, use them. Otherwise use the latest tag up to
   `HEAD`. Confirm the range in your answer.
2. **Collect the commits.** Run the bundled script from the repository root:

   ```bash
   python3 scripts/collect_commits.py --from v1.2.0 --to HEAD
   ```

   With no `--from` it starts at the most recent tag (or the first commit if there are no tags).
   Add `--format json` if you want to process the result yourself. The script groups commits by
   conventional-commit type and lists breaking changes first. Details are in
   [the commit grouping reference](reference.md).
3. **Read what is unclear.** For any commit whose subject does not explain the user-visible
   effect, look at the diff (`git show --stat <hash>`) before writing about it.
4. **Write the notes.**
   - Lead with breaking changes and what the user must do about each.
   - Then features, then fixes. Fold docs, tests, CI and refactors into one "Internal" line or
     leave them out.
   - One line per change, written for users: the effect, not the implementation.
     "Exports no longer time out on large projects", not "refactor ExportJob retry loop".
   - Merge commits that belong to one change into one line.
   - Keep issue or pull request numbers that appear in the subjects.
5. **Check before you hand it over.** Every line maps to at least one commit in the range, nothing
   is invented, and the version and date in the heading are the ones the user gave you. If you
   were not given a version number, ask or leave a clear placeholder.

## Output format

```markdown
## v1.3.0 (2025-03-14)

### Breaking changes
- ...

### Added
- ...

### Fixed
- ...
```

Follow the project's existing CHANGELOG style instead if it has one.
