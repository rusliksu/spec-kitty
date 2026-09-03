# Implementation Plan: Retire Legacy Spec Kitty Skills

## Branch Contract

- Current branch: `codex/spec-kitty-retire-legacy-skills`
- Planning/base branch: `main`
- Final merge target: `main`
- Branch matches target: no, by design; work is isolated in a task branch.

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary surfaces**: canonical skill registry, retirement authority, global
  agent-skill bootstrap tests
- **Test framework**: pytest
- **Quality gates**: targeted pytest, ruff, mypy, wheel build/inspection,
  isolated runtime smoke
- **Packaging**: Hatchling wheel for `spec-kitty-cli`

## Design

1. Add a single explicit mapping from each legacy alias to its canonical
   `spk-*` replacement in `skills/retired.py`; derive the retired-name set from
   that authority.
2. Make `SkillRegistry.discover_skills()` omit retired canonical names by
   default. Keep the bundled source directories available as historical or
   migration material, avoiding a large destructive content deletion.
3. Let the existing bootstrap cleanup seam remove only names in the explicit
   retired set and copy the remaining canonical registry. Its current version-
   lock bypass already guarantees same-version cleanup.
4. Drive the change ATDD-first: commit failing behavioral coverage before any
   production edit, then make the smallest implementation change.
5. Build a wheel and execute bootstrap with an isolated `USERPROFILE` and
   `SPEC_KITTY_HOME`; inspect that aliases are absent and replacements present.

## Ownership and Safety

The explicit finite retired-name mapping is the package-managed path contract;
no wildcard is added. Unknown skills remain untouched. All runtime smoke work
uses a temporary profile. No installation or launcher mutation is part of this
mission.

## Verification

```text
pytest tests/skills/test_registry.py tests/runtime/test_agent_skills.py
ruff check src/specify_cli/skills/retired.py src/specify_cli/skills/registry.py tests/skills/test_registry.py tests/runtime/test_agent_skills.py
mypy src/specify_cli/skills/retired.py src/specify_cli/skills/registry.py src/specify_cli/runtime/agent_skills.py
python -m build --wheel
```

The wheel smoke then runs the built candidate in a temporary virtual
environment and temporary profile, never against real global skill roots.

## Gates

- No implementation before a failing test commit.
- No push, PR transition, merge, installed-runtime replacement, launcher edit,
  or real global recovery in this package.
- Any need to widen beyond the fourteen names requires a new approval delta.
