---
work_package_id: "WP02"
title: "Local Installation and Fork Delivery"
dependencies: ["WP01"]
subtasks: ["T008", "T009", "T010", "T011", "T012", "T013"]
requirement_refs: ["FR-006", "FR-007", "NFR-004"]
execution_mode: "delivery"
owned_files:
  - "kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/**"
authoritative_surface: "kitty-specs/retire-legacy-spec-kitty-skills-01M1KADP/"
beads_id: "spk-8zh"
agent_profile: "implementer-ivan"
role: "implementer"
agent: "codex"
---

# WP02: Local Installation and Fork Delivery

## Goal

Install the exact verified legacy-skill-retirement candidate with recoverable
fallbacks, prove it repairs the real global package-managed skill root without
touching an unrelated user skill, and publish the task branch as a draft PR.

## Authorization

Ruslan explicitly approved local installation and prioritized updating the
Spec Kitty fork and current Bead on 2026-09-03. This authorization does not
include merge, release, direct push to `main`, or fallback cleanup.

## Validation

- Confirm the installed wheel hash equals the verified candidate hash.
- Confirm the launcher resolves the side-by-side runtime and reports `3.2.6rc4`.
- Run `upgrade --agent-check --json` once against the real user profile.
- Verify `.agents/skills` contains zero retired aliases and all 14 replacements.
- Verify `.codex/skills/best-step/SKILL.md` remains byte-identical.
- Re-run the focused pytest, ruff, and mypy gates before draft PR publication.

## Out of Scope

PR merge, public release, direct push to `main`, deleting old runtimes or the
launcher backup, and any separate change to the Beads codebase.
