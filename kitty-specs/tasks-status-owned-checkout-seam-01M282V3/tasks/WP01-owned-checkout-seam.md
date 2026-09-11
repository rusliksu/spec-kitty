---
work_package_id: "WP01"
title: "Owned-checkout seam for state-recording commands"
dependencies:
  []
requirement_refs:
  - FR-001
  - FR-002
  - FR-003
  - FR-004
  - FR-005
  - NFR-002
  - NFR-004
  - C-001
  - C-002
  - C-003
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
  - T006
owned_files:
  - "src/specify_cli/cli/commands/agent/tasks_move_task.py"
  - "src/specify_cli/cli/commands/agent/tasks_shared.py"
  - "src/specify_cli/cli/commands/agent/status.py"
  - "tests/tasks/test_move_task_owned_checkout_seam.py"
  - "tests/status/test_status_owned_checkout_seam.py"
  - "src/specify_cli/cli/commands/agent/tasks.py"
  - "src/specify_cli/status/models.py"
  - "src/specify_cli/status/aggregate.py"
  - "src/specify_cli/coordination/status_transition.py"
  - "src/specify_cli/missions/_read_path_resolver.py"
  - "src/mission_runtime/resolution.py"
  - "src/mission_runtime/write_target_degrade.py"
  - "tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py"
  - "tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py"
  - "tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/help/move-task.help"
  - "tests/architectural/test_no_read_side_bypass.py"
  - "tests/architectural/test_single_mission_surface_resolver.py"
authoritative_surface: "src/specify_cli/cli/commands/agent/"
execution_mode: "code_change"
plan_concern_refs:
  - IC-01
  - IC-02
planning_base_branch: codex/tasks-status-owned-checkout
merge_target_branch: codex/tasks-status-owned-checkout
branch_strategy: Planning artifacts for this mission were generated on codex/tasks-status-owned-checkout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/tasks-status-owned-checkout unless the human explicitly redirects the landing branch.
---

# Work Package Prompt: WP01 – Owned-checkout seam for state-recording commands

## Objective

Give `move-task` and the canonical status commands the same explicit `--owned-checkout` seam that
`next`, `spec-commit` and `agent mission create` already have, so a mission that lives in an owned
linked worktree can record lane transitions and review verdicts.

## Context

Issue 26 records the gap and its reproduction. `next_cmd.py` already shows the sanctioned pattern:
declare the option, bypass only the syntactic `.worktrees` guard, validate the path through
`resolve_ownership_claim`, render a refusal through the shared typed error, and use
`claim.claimed_checkout` as the repo root. Read `research.md` (D-1, D-2, D-3, D-5) and
`data-model.md` (invariants I-1..I-5) before starting.

The prototype for this seam is the mission itself: this mission was created and planned through
`--owned-checkout`, and its runtime still cannot advance past `implement` without it.

## Subtasks & Detailed Guidance

### Subtask T001 – RED: reproduce issue 26 from an owned worktree

- **Purpose**: have an executable oracle before touching production code.
- **Steps**: in `tests/tasks/test_move_task_owned_checkout_seam.py`, build a real owned worktree
  fixture (a registered linked worktree of a temporary primary) holding a `single_branch` mission with
  a tasks.md and a WP file, then invoke the CLI's move-task against it with `--owned-checkout`.
  Assert the transition is recorded in the **owned** mission's canonical status log and that the
  primary checkout's HEAD and cleanliness are unchanged.
- **Files**: `tests/tasks/test_move_task_owned_checkout_seam.py` (new).
- **Validation**: the test fails on the pre-change head with `mission_not_found`.
- **Parallel?**: No.

### Subtask T002 – Move-task honours the declaration

- **Purpose**: close the resolution half of FR-001.
- **Steps**: add `--owned-checkout` to `move-task`; when present, resolve the claim as in
  `next_cmd.py` and use `claim.claimed_checkout` as the repo root for mission resolution and for the
  status placement in `tasks_shared.py`. Reuse the ownership authority; do not add validation.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`,
  `src/specify_cli/cli/commands/agent/tasks_shared.py`.
- **Validation**: T001 turns GREEN.
- **Parallel?**: No.

### Subtask T003 – Status commands honour the declaration

- **Purpose**: FR-002 — review verdicts must be recordable.
- **Steps**: add the same option to `spec-kitty agent status emit` (and to `validate`, `lifecycle`
  for read parity), and route the canonical write to the claimed checkout.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`.
- **Validation**: an approval with `--review-result-json` from the owned worktree lands in the owned
  mission's status log (`tests/status/test_status_owned_checkout_seam.py`).
- **Parallel?**: No.

### Subtask T004 – Fail-closed refusals

- **Purpose**: FR-003.
- **Steps**: assert that an undeclared run still fails with `mission_not_found`, that a directory which
  is not a worktree of the resolved primary is refused with the typed ownership error, and that a
  refusal writes nothing.
- **Files**: both new test modules.
- **Validation**: refusals are typed and non-mutating.
- **Parallel?**: No.

### Subtask T005 – Primary checkout proof

- **Purpose**: NFR-004, FR-004.
- **Steps**: record the primary checkout's HEAD, index and file set before and after each acceptance
  run and assert they are unchanged.
- **Files**: both new test modules.
- **Validation**: the proof is part of the acceptance test, not a manual note.
- **Parallel?**: No.

### Subtask T006 – No-opt-in parity

- **Purpose**: FR-005, C-001.
- **Steps**: run the existing move-task and status command suites unchanged and assert they pass; add a
  case that the guarded path still refuses from a worktree when no checkout is declared.
- **Files**: existing suites (read-only) plus the new modules.
- **Validation**: no expectation in the existing suites changes.
- **Parallel?**: No.

## Definition of Done

- `move-task` and `status emit` accept `--owned-checkout` and record the transition for the mission in
  the declared checkout.
- An undeclared run behaves exactly as before; an invalid declaration is refused with the shared typed
  error and writes nothing.
- The primary checkout proves unchanged in every acceptance run.
- `ruff`, `mypy`, `compileall` and `git diff --check` are clean on the changed files.
- No new skip, xfail or deselection.

## Risks

- **Routing**: the status writer may need an explicit owned-mission route for `single_branch`; if so it
  must reuse the existing writer (C-002) — no second authority.
- **Overlap**: PR 20 implements its own move-task routing; keep this change additive and record the
  difference rather than merging the two by hand.
- **Test fixtures**: an owned worktree fixture must be real (registered worktree, real mission files);
  a temp-directory shortcut would not reproduce the defect.

## Reviewer Guidance

Check that the option is honoured only when declared, that the ownership authority is reused and not
re-implemented, that no write can reach the primary checkout, and that the no-opt-in path is provably
unchanged. Reject any approach that resolves the mission by scanning the ambient working directory.
