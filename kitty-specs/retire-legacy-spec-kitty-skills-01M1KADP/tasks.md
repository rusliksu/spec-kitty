# Tasks: Retire Legacy Spec Kitty Skills

**Mission**: `retire-legacy-spec-kitty-skills-01M1KADP`
**Bead**: `spk-8zh`

## Work Package Roadmap

| WP | Goal | Requirements | Dependencies |
|---|---|---|---|
| WP01 | Retire aliases and prove migration behavior | FR-001–FR-005, NFR-001–NFR-003 | none |
| WP02 | Install the candidate and publish the fork branch | FR-006–FR-007, NFR-004 | WP01 |

## WP01 — Registry Retirement and Bootstrap Migration

- [x] T001 Add failing registry and current-lock bootstrap acceptance tests.
- [x] T002 Commit the RED acceptance boundary separately.
- [x] T003 Add the single legacy-to-canonical retirement mapping.
- [x] T004 Filter retired aliases from default canonical discovery.
- [x] T005 Run targeted pytest, ruff, and mypy gates.
- [x] T006 Build and inspect a wheel; run bootstrap against an isolated profile.
- [x] T007 Record evidence, review the aggregate diff, and update Bead status.

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

## WP02 — Local Installation and Fork Delivery

- [x] T008 Publish the nine pre-existing failures to non-duplicative tracker
  records and link the existing read-only issue.
- [x] T009 Install the exact verified wheel in a side-by-side runtime.
- [x] T010 Back up and update the user launcher while retaining prior fallbacks.
- [x] T011 Run real-profile startup and verify aliases, replacements, and an
  unrelated user-skill hash.
- [x] T012 Re-run targeted tests, ruff, and mypy on the final branch.
- [x] T013 Push the task branch and open draft PR `rusliksu/spec-kitty#5`.
- [x] T014 Run a three-profile adversarial review and capture the convergent
  user-skill deletion blocker.
- [x] T015 Add a behavioral RED, constrain cleanup to the retired-name set, and
  verify both global roots.
- [x] T016 Rebuild the wheel, install it side-by-side, and switch the launcher
  while retaining the previous candidate as a fallback.

**Owned repository files**:

- `kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/**`

**Authorized local surfaces**:

- `C:/Users/Ruslan/.local/share/spec-kitty-retire-legacy-skills-e3f0846fa/`
- `C:/Users/Ruslan/.local/share/spec-kitty-retire-legacy-skills-30e790867/`
- `C:/Users/Ruslan/spec-kitty.cmd`

**Independent acceptance**: inspect the installation evidence in
`verification.md`, re-run the focused quality gates, and review the draft PR.
