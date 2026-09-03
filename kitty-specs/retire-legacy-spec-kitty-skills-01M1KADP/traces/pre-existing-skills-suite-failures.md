# Pre-existing Skills-suite Failures

## Status

All nine failures left after the mission-attributable verifier fixture fix were
reproduced without the mission changes on a clean detached worktree of
`origin/main`:

- Baseline commit: `87d851382fc50cd789ba542b28dbc4bc0fb37618`
- Result: `9 failed in 182.99s (0:03:02)`
- Import proof: `specify_cli` resolved from the detached baseline worktree
- Post-run worktree state: clean (`git status --porcelain` returned no entries)
- Cleanup: the detached worktree and isolated profile were removed

This proves that these nine failures are not regressions introduced by mission
`retire-legacy-spec-kitty-skills-01M1KADP`.

## Reproduction

Run these node IDs on Windows against the baseline commit with an isolated
`USERPROFILE` and `SPEC_KITTY_HOME`:

```text
python -m pytest \
  tests/specify_cli/skills/test_command_renderer.py::test_description_from_frontmatter_takes_priority \
  tests/specify_cli/skills/test_e2e.py::test_full_lifecycle \
  tests/specify_cli/skills/test_e2e.py::test_per_class_distribution \
  tests/specify_cli/skills/test_e2e.py::test_drift_detection_and_repair \
  tests/specify_cli/skills/test_e2e.py::test_multiple_agents_mixed_classes \
  tests/specify_cli/skills/test_installer.py::TestInstallNativeRootAgent::test_files_placed_in_native_root \
  tests/specify_cli/skills/test_installer.py::TestInstallSharedRootAgent::test_files_placed_in_shared_root \
  tests/specify_cli/skills/test_installer.py::TestManifestEntriesCreated::test_entry_fields_correct \
  tests/specify_cli/skills/test_installer.py::TestInstallCopiesReferencesAndScripts::test_entry_source_file_is_relative_within_skill \
  -q -p no:cacheprovider
```

## Failure groups

### Manifest paths use Windows separators

Six assertions expect portable `/` separators but receive `\`:

- `test_per_class_distribution`
- `test_multiple_agents_mixed_classes`
- `TestInstallNativeRootAgent::test_files_placed_in_native_root`
- `TestInstallSharedRootAgent::test_files_placed_in_shared_root`
- `TestManifestEntriesCreated::test_entry_fields_correct`
- `TestInstallCopiesReferencesAndScripts::test_entry_source_file_is_relative_within_skill`

### Installed skill files remain read-only

Two lifecycle tests cannot delete a copied `SKILL.md` on Windows and raise
`PermissionError: [WinError 5]`:

- `test_full_lifecycle`
- `test_drift_detection_and_repair`

This defect class is already tracked by open GitHub issue `#3771`, "Windows:
skill content migrations fail with WinError 5 on ReadOnly managed SKILL.md".

### Renderer frontmatter precedence

One renderer test expects the explicit description `Frontmatter wins`, but the
parsed value is `Should not appear in description`:

- `test_description_from_frontmatter_takes_priority`

## Issue-ready drafts

### Portable manifest paths

Title:

```text
Windows: serialize skill manifest paths with portable separators
```

Body:

```text
The skills suite currently has six reproducible path failures on Windows at
origin/main commit 87d851382fc50cd789ba542b28dbc4bc0fb37618.

Manifest and installer entries receive backslashes instead of portable forward
slashes in installed_path and source_file. The failures are:
- test_per_class_distribution
- test_multiple_agents_mixed_classes
- TestInstallNativeRootAgent::test_files_placed_in_native_root
- TestInstallSharedRootAgent::test_files_placed_in_shared_root
- TestManifestEntriesCreated::test_entry_fields_correct
- TestInstallCopiesReferencesAndScripts::test_entry_source_file_is_relative_within_skill

The exact node IDs and reproduction command are recorded in
kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/traces/
pre-existing-skills-suite-failures.md.

Acceptance:
- all six node IDs pass on Windows;
- serialized manifest paths remain portable across platforms;
- no regression in the broader skills suite.
```

### Renderer frontmatter precedence

Title:

```text
skills: preserve explicit description frontmatter in command renderer
```

Body:

```text
test_description_from_frontmatter_takes_priority fails at origin/main commit
87d851382fc50cd789ba542b28dbc4bc0fb37618.

The fixture expects the explicit description "Frontmatter wins", but the
rendered skill frontmatter contains body-derived text, "Should not appear in
description".

The exact node ID and reproduction command are recorded in
kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/traces/
pre-existing-skills-suite-failures.md.

Acceptance:
- the focused node ID passes;
- explicit frontmatter description wins over body-derived text;
- existing renderer behavior remains covered by the broader skills suite.
```

## Published tracker records

- Read-only-file failures: `#3771`, with baseline reproduction added in comment
  `#issuecomment-5524540603`.
- Portable-path failures: `#3852`.
- Renderer-frontmatter failure: `#3853`.

Published on 2026-09-03 after explicit operator authorization.
