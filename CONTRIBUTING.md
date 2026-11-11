# Contributing

New skills, fixes to existing ones and new lint rules are all welcome.

## Adding or changing a skill

1. Read [skills/skill-authoring/SKILL.md](skills/skill-authoring/SKILL.md) and start from
   [its template](skills/skill-authoring/template.md).
2. Keep the skill tool-agnostic: no product-specific tool names, no links outside the folder,
   scripts that run with a stock `python3`, `bash` or `node`.
3. If the skill ships a script, add tests for it in `tests/test_skill_scripts.py` and sample
   input under `examples/`. Sample data must be invented.
4. Run the checks CI runs:

   ```bash
   pip install -e ".[dev]"
   skill-lint skills --strict
   pytest
   ```

## Changing the validator

Each rule lives in `skill_lint/checks.py` and has a stable id shown in square brackets in the
output. Add a test in `tests/test_checks.py` for every new rule, and list it in the README table.
