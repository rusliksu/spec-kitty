---
work_package_id: WP02
title: Read-Side Planning Consumer Adoption
dependencies:
- WP01
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
- T005
- T006
- T007
- T008
phase: Phase 2 - Read-side adoption
history:
- at: '2026-09-03T20:41:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
- tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Read-Side Planning Consumer Adoption

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make `check-prerequisites` and `setup-plan` consume the existing canonical Mission operation context so exact linked-worktree selectors resolve the caller-owned Mission without changing Git-topology authority or fail-closed behavior.

## Context and Constraints

- WP01 must be approved with a verified RED commit.
- Reference `agent context resolve` and `src/specify_cli/missions/operation_context.py` for the intended authority split.
- `repository_root` remains the primary Git/protection authority.
- `mission_anchor_root` selects Mission identity and planning artifacts.
- Do not add a new Mission census, directory walk, environment override, or raw CWD fallback.
- Keep historical patch seams used by unit tests unless migration deliberately updates their tests.

## Branch Strategy

- **Strategy**: Continue the same sequential lane after WP01.
- **Planning base branch**: `codex/check-prerequisites-task-worktree-resolution`
- **Internal merge target**: `codex/check-prerequisites-task-worktree-resolution`
- **External pull-request target**: fork `main`

Execution worktrees are allocated from `lanes.json`; use the WP02 workspace derived by the runtime and never edit the primary checkout.

```text
spec-kitty agent action implement WP02 --agent codex
```

## Subtasks and Detailed Guidance

### T005 — Adopt operation context in check-prerequisites

**Purpose**: Make the exact command emitted by context resolution executable.

**Steps**:

1. Resolve the canonical repository root exactly once through the existing command seam.
2. Resolve `MissionOperationContext` using the explicit selector and invocation cwd.
3. Retain repository-root Git preflight and protection behavior.
4. Validate and report the feature directory under `mission_anchor_root` using the canonical identity.
5. Preserve resume-probe rules, structured JSON envelopes, legacy primary behavior, and error codes.
6. Remove only the primary-only branch that conflicts with the selected operation context.

**Reviewer invariant**: A caller-owned hit must not trigger `_list_feature_spec_candidates()` merely because primary lacks the Mission.

### T006 — Adopt operation context in setup-plan

**Purpose**: Ensure the workflow does not fail immediately after prerequisites.

**Steps**:

1. Select the same operation context before reading spec or creating plan artifacts.
2. Check substantive/committed spec against the selected Mission and task branch, not primary HEAD.
3. Keep plan-template generation and commit boundaries unchanged after selection.
4. Preserve primary-only and coordination-topology behavior for Missions that resolve there.
5. Keep missing/ambiguous/conflicting selectors structured and fail closed.

### T007 — Extend focused unit coverage

**Purpose**: Localize regressions in each consumer in addition to WP01 integration coverage.

**Steps**:

1. Add direct tests for operation-context selection and root forwarding at existing patch seams.
2. Assert repository and Mission roots are not accidentally swapped.
3. Preserve existing envelope keys and branch output.
4. Cover the primary-only compatibility path and conflict propagation.
5. Avoid assertions on incidental implementation order unless it is an authority invariant.

### T008 — Close read-side RED cases

**Purpose**: Demonstrate the minimal production change fixes the intended half of the contract.

**Steps**:

1. Run WP01 with only prerequisite/setup tests selected and require green.
2. Run both complete consumer unit suites.
3. Run operation-context and resolver architectural guards.
4. Verify primary checkout snapshots remain identical.
5. Commit the production/read-side tests separately from WP01 RED.

## Test Strategy

```powershell
uv run --extra test pytest -q tests/tasks/test_linked_worktree_planning_context.py -k "prerequisite or setup_plan"
uv run --extra test pytest -q tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py tests/architectural/test_mission_resolver_walker_gate.py tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py
```

## Definition of Done

- Slug and immutable-ID paths are green for both consumers.
- Existing missing/ambiguous/primary cases remain green.
- No command-local scan or new resolver exists.
- Primary HEAD and files are unchanged in real-Git cases.
- Ruff, targeted strict mypy, compileall, and diff-check pass for owned files.

## Risks and Mitigations

- **Risk**: Treating anchor as repository root. **Mitigation**: name and test each root separately.
- **Risk**: Breaking old patch seams. **Mitigation**: extend closest unit suites and preserve deferred imports where required.
- **Risk**: Broad read-path rewrite. **Mitigation**: constrain edits to owned consumers unless WP01 proves a seam defect.

## Review Guidance

Trace every artifact read to `mission_anchor_root` and every Git-policy operation to `repository_root`. Reject any silent primary fallback after a caller-owned exact hit or any weakened ambiguity error.

## Activity Log

- 2026-09-03T20:41:12Z – system – Prompt created.
