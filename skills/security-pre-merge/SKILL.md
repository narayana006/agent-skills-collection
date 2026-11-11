---
name: security-pre-merge
description: Review a branch or diff for security problems before it is merged. Use when the user asks for a security review, a pre-merge check, or "is this safe to merge", or when a change touches authentication, input handling, secrets, file access, SQL or shell commands.
---

# Security pre-merge review

Review only what the change introduces. The goal is a short list of real, exploitable problems,
not a catalogue of everything that could be better.

## Steps

1. **Get the diff.** Use the base branch the user names; default to `main`.

   ```bash
   git diff main...HEAD > /tmp/change.diff
   ```

2. **Run the pattern scan** on the added lines:

   ```bash
   python3 scripts/scan_diff.py /tmp/change.diff
   ```

   It also reads a diff from standard input. It flags likely secrets and a small set of risky
   constructs, and exits with status 1 when it finds anything of high severity. Treat its output
   as leads to verify, not as the review: it sees single lines, not data flow.
3. **Walk the checklist** in [checklist.md](checklist.md) against every changed file. For each
   item decide: not applicable, fine, or a finding.
4. **Trace untrusted input.** For each new entry point (route, handler, CLI argument, message
   consumer, file parser), follow the input to where it is used. This is where the real findings
   are, and no pattern scan will do it for you.
5. **Verify each finding** before reporting it. Read the surrounding code, and check whether a
   framework default, a validator or middleware already handles it. Drop anything you cannot
   explain an attack for.
6. **Report.**

## Report format

For each finding, most severe first:

- **Severity** (high, medium, low) and a one-line title
- **Where**: file and line
- **What can go wrong**: the concrete attack, in one or two sentences
- **Fix**: the smallest change that closes it

Finish with what you checked and found clean, and what you could not check (for example
infrastructure configuration that is not in the repository). If there are no findings, say so
plainly instead of padding the report.

## Rules

- Never print a discovered secret in full. Show the first four characters and the location, and
  tell the user to rotate it: removing it from the branch does not remove it from history.
- Do not report style issues, missing tests or general hardening advice as security findings.
