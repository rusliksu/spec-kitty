# Verification Evidence

## RED

Command:

```text
python -m pytest tests/specify_cli/skills/test_registry.py tests/runtime/test_agent_skills.py -q
```

Result on the pre-implementation test commit: collection failed twice because
`RETIRED_LEGACY_SKILL_REPLACEMENTS` did not exist. This is the intended RED
contract.

## GREEN

- Focused registry/bootstrap run: `19 passed in 75.92s`.
- Focused registry/bootstrap/verifier/doctrine/migration run:
  `37 passed in 82.37s`.
- Ruff: `All checks passed!`.
- Mypy: `Success: no issues found in 3 source files`.

All pytest processes used a temporary `USERPROFILE` and
`SPEC_KITTY_HOME`; no real global skill root was a fixture.

## Candidate

- Wheel: `spec_kitty_cli-3.2.6rc4-py3-none-any.whl`
- Size: `8,295,502` bytes
- SHA-256: `99E68A2DC683F0F2A026CB20BEBE825C27D1BFBE24E0C09F3C8608B08A2D00CE`
- Location:
  `C:/Users/Ruslan/AppData/Local/Temp/codex-spec-kitty-retire-legacy-skills-candidates/ce9518f47182420197ace8a8f68e8ca5/`
- Installed-wheel registry: `DISCOVERED=41 ALIASES=0 REPLACEMENTS=14`.
- Startup bootstrap in isolated profile:
  `ALIASES_REMAINING=0 CANONICAL_MISSING=0 CUSTOM_PRESERVED=True`.

The initial `--version` smoke was invalid because Typer handles that eager
option before the startup callback. The valid smoke used
`upgrade --agent-check --json` and then inspected only skill directories.

## Open Gate

An exploratory broad skills-suite run produced `285 passed, 10 failed`. One
failure was attributable to this mission and was fixed by moving its verifier
fixture from retired `spec-kitty` to canonical `spk-start-here`. The remaining
nine failures are in unchanged Windows path/read-only and command-renderer
surfaces. No matching open GitHub issue was found. Repository policy requires a
GitHub issue before treating those failures as accepted baseline; public issue
creation is not authorized by the current bounded task.
