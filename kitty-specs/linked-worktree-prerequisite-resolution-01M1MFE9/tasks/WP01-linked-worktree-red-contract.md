---
work_package_id: WP01
title: Linked-Worktree RED Contract Harness
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: codex/check-prerequisites-task-worktree-resolution
merge_target_branch: codex/check-prerequisites-task-worktree-resolution
branch_strategy: Planning artifacts for this mission were generated on codex/check-prerequisites-task-worktree-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/check-prerequisites-task-worktree-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Executable contract
history:
- at: '2026-09-03T20:41:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/tasks/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/tasks/test_linked_worktree_planning_context.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Linked-Worktree RED Contract Harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Create an executable, real-Git RED contract that reproduces every planning command's loss of caller-owned linked-worktree Mission context. Commit tests separately before any production change. A failure is useful only when it points to the current primary-only resolution behavior.

## Context and Constraints

- Read `../spec.md`, `../plan.md`, `../contracts/operation-context-consumer.md`, and `../quickstart.md` before editing.
- Existing `agent context resolve` is reference evidence because it already uses `resolve_mission_operation_context()`.
- Do not edit production files in this WP.
- Do not weaken or rewrite existing assertions to manufacture RED.
- Use a temporary primary repository plus a registered linked worktree; a plain copied directory is insufficient.
- Snapshot primary branch HEAD and working-tree status before every write-capable command.
- The Windows missing-`fcntl` origin-binding issue is out of scope.

## Branch Strategy

- **Strategy**: Single sequential code lane; WP01 precedes every production package.
- **Planning base branch**: `codex/check-prerequisites-task-worktree-resolution`
- **Internal merge target**: `codex/check-prerequisites-task-worktree-resolution`
- **External pull-request target**: fork `main`

When `lanes.json` is available, enter only the workspace allocated to WP01. Until bootstrap finalization is possible, remain in the validated task worktree and do not create an ad-hoc lane.

Implementation command after valid finalization:

```text
spec-kitty agent action implement WP01 --agent codex
```

## Subtasks and Detailed Guidance

### T001 — Build the linked-worktree Mission fixture

**Purpose**: Reproduce the topology that the existing unit tests miss.

**Steps**:

1. Create a temporary Git primary checkout with the minimum project markers required by `locate_project_root()`.
2. Commit the initial primary state and create a registered linked worktree on a distinct task branch.
3. Place a substantive Mission only in the linked worktree with valid `meta.json`, `spec.md`, `plan.md`, status log, and task scaffold as required by the invoked command.
4. Use a deterministic Mission slug and immutable ID so the same fixture can exercise both handle forms.
5. Provide helpers that capture primary HEAD, porcelain status, and Mission-tree contents before and after each command.

**Files**: `tests/tasks/test_linked_worktree_planning_context.py`.

**Validation**: Prove Git recognizes the secondary checkout as a worktree and that the Mission is absent from primary.

### T002 — Add RED prerequisite and plan-setup cases

**Purpose**: Pin the read-side consumer failures.

**Steps**:

1. Invoke the actual `agent mission check-prerequisites` command from the linked worktree with the full slug.
2. Repeat with the immutable Mission ID.
3. Assert the future success contract: absolute linked-worktree `feature_dir`, correct current/target branch, and no 442-Mission-style census fallback.
4. Invoke `agent mission setup-plan` against the same committed substantive spec and assert it selects the same Mission surface.
5. Confirm current base fails for the expected primary-only reason; record the exact failing assertions in the RED commit message or evidence.

**Validation**: Existing primary-only happy paths must continue to pass when the new tests are run together with their closest suites.

### T003 — Add RED decision and spec-commit cases

**Purpose**: Prevent a partial repair that only moves the first blocker.

**Steps**:

1. Invoke decision open and verify using the linked-worktree-only Mission.
2. Assert the decision artifact/event belongs to the selected immutable identity and linked Mission surface.
3. Invoke spec-commit with a file under the linked Mission and assert it does not diagnose protected primary as the selected artifact surface.
4. Keep all command routing real; patch external network or unrelated services only.
5. Restore fixture state between write-capable cases so failures are independent.

### T004 — Pin fail-closed and cleanliness controls

**Purpose**: Ensure caller preference cannot become unsafe fallback.

**Steps**:

1. Cover missing, omitted-in-multi-Mission, ambiguous, and unsafe/path-like selectors.
2. Create a primary/caller selector collision with different immutable IDs and require typed conflict refusal.
3. Assert every failed command leaves primary HEAD and porcelain status unchanged.
4. Assert successful future linked-worktree cases also leave primary unchanged.
5. Run `git diff --check` and commit only the new test file as the RED boundary.

## Test Strategy

```powershell
uv run --extra test pytest -q tests/tasks/test_linked_worktree_planning_context.py
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py
```

The first command must be RED for the intended consumer-routing reason. The second must remain green.

## Definition of Done

- Four subtasks are represented by clear tests in the owned file.
- RED is reproducible without timing assumptions or platform-specific skips.
- Primary cleanliness and conflicting-identity controls are executable.
- No production file changed.
- A dedicated RED commit exists and its failure evidence is recorded.

## Risks and Mitigations

- **Risk**: Fixture bypasses `locate_project_root`. **Mitigation**: invoke actual CLI entry points from the registered worktree cwd.
- **Risk**: Write-capable tests leak state. **Mitigation**: isolate each case and snapshot both repositories.
- **Risk**: Tests couple to human error prose. **Mitigation**: assert structured codes and authoritative paths first.

## Review Guidance

Reject if tests use only mocks, create an unregistered directory, omit immutable-ID coverage, or fail to prove primary cleanliness. Verify the RED reason on the planning base before approving implementation work.

## Activity Log

- 2026-09-03T20:41:12Z – system – Prompt created.
