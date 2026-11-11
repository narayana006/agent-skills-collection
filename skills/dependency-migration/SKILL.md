---
name: dependency-migration
description: Plan and carry out a dependency or framework upgrade or replacement in small, verifiable steps. Use when the user asks to upgrade a major version, replace one library with another, or migrate off a deprecated package or API.
---

# Dependency and framework migration

Migrations fail when they are done in one large change with no way to tell which edit broke what.
Work in small steps and keep the test suite green between them.

## Steps

1. **Establish the baseline.** Run the tests and the build before touching anything. Write down
   what already fails so you do not chase old failures later. If there are no tests around the
   code that uses the dependency, say so and propose adding a few first.
2. **Measure the surface.** From the repository root run:

   ```bash
   python3 scripts/usage_report.py <package-name> .
   ```

   It lists every file that imports the package (Python, JavaScript and TypeScript), with line
   numbers and the names imported, sorted by number of uses. Use it to size the work and to
   decide the order. Add `--format json` for machine-readable output.
3. **Read the upstream migration guide and changelog** for every major version you cross. List
   the breaking changes that apply to the names found in step 2; ignore the rest.
4. **Write the plan** and show it to the user before editing:
   - target version, and intermediate versions if a direct jump is not supported
   - each breaking change that applies, with the files it touches
   - the order: leaf modules first, shared helpers last
   - how each step will be verified
5. **Migrate one step at a time.** Change the version, fix one group of call sites, run the
   tests, commit. Prefer an official codemod when one exists, and review its diff.
6. **Deal with what the type checker and tests cannot see:** configuration files, environment
   variables, CLI flags in scripts and CI, serialised data formats, default values that changed.
7. **Finish.** Remove compatibility shims and the old package, regenerate the lockfile, rerun the
   usage report to confirm nothing is left, and summarise what changed in behaviour.

## Rules

- Do not mix the migration with unrelated refactoring.
- Do not silence a failing test to get through a step. Either fix it or stop and report it.
- If a step turns out much larger than planned, stop and revise the plan with the user.
