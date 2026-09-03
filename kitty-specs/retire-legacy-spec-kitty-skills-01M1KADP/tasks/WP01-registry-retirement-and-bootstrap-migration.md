---
work_package_id: "WP01"
title: "Registry Retirement and Bootstrap Migration"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005", "T006", "T007"]
requirement_refs: ["FR-001", "FR-002", "FR-003", "FR-004", "FR-005"]
execution_mode: "code_change"
owned_files:
  - "src/specify_cli/skills/retired.py"
  - "src/specify_cli/skills/registry.py"
  - "tests/specify_cli/skills/test_registry.py"
  - "tests/specify_cli/skills/test_verifier.py"
  - "tests/runtime/test_agent_skills.py"
  - "docs/changelog/CHANGELOG.md"
  - "kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/**"
authoritative_surface: "src/specify_cli/skills/"
beads_id: "spk-8zh"
agent_profile: "implementer-ivan"
role: "implementer"
agent: "codex"
---

# WP01: Registry Retirement and Bootstrap Migration

## Goal

Stop default canonical discovery and startup bootstrap from republishing the
fourteen approved legacy aliases while preserving canonical replacements and
unrelated user skills.

## ⚡ Do This First

Add the behavioral tests and prove they fail on `main`/the planning base before
editing production code. Commit that RED boundary separately.

## Implementation Contract

- Keep one explicit legacy-to-canonical mapping as the naming authority.
- Default registry discovery excludes every mapping key.
- Existing bootstrap cleanup removes stale mapping-key directories even with a
  current version lock.
- Do not delete bundled legacy source directories in this WP.
- Do not broaden cleanup to unknown names or touch any real user-global root.

## Validation

Run the targeted commands in `plan.md`. Build a wheel, inspect default registry
discovery from that wheel, and run startup under temporary `USERPROFILE` and
`SPEC_KITTY_HOME` paths. Record commands and outcomes in the mission traces and
Bead notes.

## Out of Scope

Installation, launcher replacement, real global skill recovery, push, PR state
changes, and merge.
