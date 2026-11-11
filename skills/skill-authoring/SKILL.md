---
name: skill-authoring
description: Write a new agent skill or improve an existing one, as a folder with a SKILL.md file and optional scripts. Use when the user asks to create a skill, turn a repeated workflow or set of instructions into a skill, or fix a skill that an agent does not pick up or follows badly.
---

# Writing a skill

A skill is a folder an agent can load when a task matches it. The agent first sees only the
`name` and `description` from the frontmatter; the rest of `SKILL.md` is read once the skill is
chosen, and other files only when the instructions point to them. Write with that in mind.

## Steps

1. **Pin down the job.** Ask for, or write down, two or three concrete requests that should
   trigger the skill and what a good result looks like for each. If you cannot, the skill is
   too vague to write yet.
2. **Create the folder.** Copy [template.md](template.md) to `<skill-name>/SKILL.md`. The folder
   name and the `name` field must be identical: lowercase letters, digits and single hyphens,
   at most 64 characters.
3. **Write the description first.** It decides whether the skill is ever used. State what the
   skill does, then when to use it, using the words a user would actually type. Plain text, at
   most 1024 characters, third person.
   - Weak: `Helps with releases.`
   - Better: `Write release notes from git history. Use when the user asks for release notes,
     a changelog, or what changed since the last release.`
4. **Write the body as instructions to a capable colleague.** Numbered steps for the workflow,
   the reasons behind any rule that is not obvious, and the exact output format expected. Leave
   out what any competent agent already knows.
5. **Move bulk out of SKILL.md.** Long reference tables, checklists and examples go in their own
   files next to it, linked with relative Markdown links. Keep `SKILL.md` under roughly 500 lines.
6. **Script what must be exact.** If a step is mechanical and has to give the same result every
   time (parsing, counting, scanning), put it in `scripts/` and tell the agent the exact command.
   Scripts should run with a standard interpreter and no installation, read arguments or stdin,
   print to stdout and use the exit status to signal failure.
7. **Keep it tool-agnostic.** Do not rely on one agent product's tool names or directory layout.
   Refer to bundled files by paths relative to the skill folder, and never link outside it: the
   folder gets copied on its own.
8. **Validate.** From the root of this repository:

   ```bash
   skill-lint path/to/skills
   ```

   Fix every error. Read the warnings; they are usually right.
9. **Try it.** Give an agent one of the requests from step 1 with the skill installed. Watch
   where it hesitates or goes wrong, and fix the instructions rather than adding more of them.

## Common mistakes

- A description that says what the skill is but not when to use it.
- Instructions written as a wall of rules in capitals instead of steps with reasons.
- Scripts mentioned in the text that were renamed or never added.
- A skill that tries to cover three workflows. Split it.
