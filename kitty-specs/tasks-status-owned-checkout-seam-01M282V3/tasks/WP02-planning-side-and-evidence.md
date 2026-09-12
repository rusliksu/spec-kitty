---
work_package_id: "WP02"
title: "Planning-side honour-or-refuse and evidence closure"
dependencies:
  - WP01
requirement_refs:
  - FR-006
  - NFR-001
  - NFR-003
  - C-004
subtasks:
  - T007
  - T008
  - T009
  - T010
owned_files:
  - "src/specify_cli/cli/commands/agent/tasks.py"
  - "src/specify_cli/cli/commands/agent/mission_finalize.py"
  - "src/specify_cli/cli/commands/research.py"
  - "kitty-specs/tasks-status-owned-checkout-seam-01M282V3/traces/**"
authoritative_surface: "src/specify_cli/cli/commands/"
execution_mode: "planning_artifact"
planning_base_branch: codex/tasks-status-owned-checkout
merge_target_branch: codex/tasks-status-owned-checkout
branch_strategy: Planning artifacts for this mission were generated on codex/tasks-status-owned-checkout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/tasks-status-owned-checkout unless the human explicitly redirects the landing branch.
---

# Work Package Prompt: WP02 – Planning-side honour-or-refuse and evidence closure

## Objective

Stop the planning-side commands from writing artifacts into the protected primary checkout when the
mission lives in an owned worktree — they must either honour the same seam or refuse loudly — and close
the mission with both-platform evidence.

## Context

During mission `sync-capture-coalescing-integrity-01M25WZF`, `spec-kitty research` wrote four scaffold
files into the protected primary checkout because it has no owned-checkout seam; they had to be moved by
hand and the primary cleaned (`research.md` D-7). `spec-kitty tasks` and
`agent tasks finalize-tasks` likewise could not see the mission. FR-006 makes "never write into the
primary" the contract.

## Subtasks & Detailed Guidance

### Subtask T007 – Planning-side commands either honour the seam or refuse

- **Purpose**: FR-006.
- **Steps**: give `research` and the task finalisation commands the same explicit option; where a
  command genuinely cannot honour it, make it refuse with an actionable message before writing anything.
  Prove the primary checkout is untouched in both outcomes.
- **Files**: `src/specify_cli/cli/commands/research.py`,
  `src/specify_cli/cli/commands/agent/tasks.py`,
  `src/specify_cli/cli/commands/agent/mission_finalize.py`.
- **Validation**: a run from an owned worktree either writes inside it or refuses; the primary proves
  unchanged.
- **Parallel?**: No.

### Subtask T008 – Issue-26 reproduction recorded end to end

- **Purpose**: NFR-001.
- **Steps**: run the exact command sequence from issue 26 against a real owned worktree of this mission's
  fixtures and record every command with its outcome.
- **Files**: none; output feeds T009.
- **Validation**: no `mission_not_found` for a mission that exists in the declared checkout.
- **Parallel?**: No.

### Subtask T009 – Evidence trace

- **Purpose**: put the evidence where the pipeline reads it.
- **Steps**: write `traces/owned-checkout-seam-evidence.md` with the RED/GREEN acceptance output, the
  refusal cases, the primary-unchanged proofs, the local suite results, and the POSIX CI verdicts at one
  candidate SHA. Append the same facts to Bead `spk-8o2`.
- **Files**: `kitty-specs/tasks-status-owned-checkout-seam-01M282V3/traces/owned-checkout-seam-evidence.md`.
- **Validation**: every claim carries a command, a URL or a job id.
- **Parallel?**: No.

### Subtask T010 – Delivery

- **Purpose**: land the seam.
- **Steps**: push the mission branch and open the delivery pull request to `main`; record the CI verdicts;
  state any residual gate explicitly.
- **Files**: none.
- **Validation**: the PR head is green, or the residual failure is classified and not candidate-owned.
- **Parallel?**: No.

## Definition of Done

- No planning-side command can write into the protected primary for a mission that lives elsewhere.
- The issue-26 reproduction is recorded end to end with no `mission_not_found`.
- The evidence trace exists, the Bead carries the same facts, and the delivery PR is published with its
  CI verdicts.
- No new skip, xfail or deselection.

## Risks

- **Scope**: research scaffolding is shared with the primary mission flow; the change must not alter that
  flow when no checkout is declared.
- **Overlap with PR 20**: recorded, not resolved by hand.

## Reviewer Guidance

Check that refusal happens before any write, that the primary checkout proof is real, and that the
evidence names one candidate SHA throughout. Reject a fix that simply ignores the primary write failure.
