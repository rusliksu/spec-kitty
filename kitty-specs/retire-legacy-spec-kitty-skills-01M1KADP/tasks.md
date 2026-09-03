# Tasks: Retire Legacy Spec Kitty Skills

**Mission**: `retire-legacy-spec-kitty-skills-01M1KADP`
**Bead**: `spk-8zh`

## Work Package Roadmap

| WP | Goal | Requirements | Dependencies |
|---|---|---|---|
| WP01 | Retire aliases and prove migration behavior | FR-001–FR-005, NFR-001–NFR-003 | none |

## WP01 — Registry Retirement and Bootstrap Migration

- [x] T001 Add failing registry and current-lock bootstrap acceptance tests.
- [x] T002 Commit the RED acceptance boundary separately.
- [x] T003 Add the single legacy-to-canonical retirement mapping.
- [x] T004 Filter retired aliases from default canonical discovery.
- [x] T005 Run targeted pytest, ruff, and mypy gates.
- [x] T006 Build and inspect a wheel; run bootstrap against an isolated profile.
- [ ] T007 Record evidence, review the aggregate diff, and update Bead status.

**Owned files**:

- `src/specify_cli/skills/retired.py`
- `src/specify_cli/skills/registry.py`
- `tests/specify_cli/skills/test_registry.py`
- `tests/specify_cli/skills/test_verifier.py`
- `tests/runtime/test_agent_skills.py`
- `docs/changelog/CHANGELOG.md`
- `kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/**`

**Independent acceptance**: a reviewer can run the verification commands from
`plan.md`, inspect the wheel registry, and confirm the isolated profile contains
canonical replacements but none of the fourteen aliases.
