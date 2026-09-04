# Quickstart: Linked Worktree Prerequisite Resolution

## Isolation

```powershell
Set-Location C:\Users\Ruslan\.codex-worktrees\spec-kitty-check-prerequisites-task-worktree-resolution
git status --short --branch
```

Expected branch: `codex/check-prerequisites-task-worktree-resolution`.

## Historical product RED contract (not final acceptance)

```powershell
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/test_safe_commit_cmd.py -k "linked_worktree or owned_checkout"
```

On the recorded pre-fix baseline, product tests must fail for the documented
consumer re-anchoring reason while operation-context controls stay green. Keep
the exact SHA and node IDs; this historical checkpoint does not approve WP01.

## WP01 harness acceptance

The approved planning correction assigns WP01 a reusable harness and its own
acceptance suite (`tests/tasks/linked_worktree_harness.py` and
`tests/tasks/test_linked_worktree_harness.py`). These are planned deliverables,
not files created by the planning correction. Drive their acceptance RED-to-GREEN,
then run the complete harness suite and operation-context controls before review.
The existing mixed product contract remains intact for final WP03 closure.

## GREEN and integration

Before WP03 approval/Mission acceptance, run this complete focused inventory plus
the new harness and existing `tests/tasks/test_linked_worktree_planning_context.py`
without `-k` filters on both Windows and POSIX CI at the same candidate SHA.
Record commands, source/interpreter paths, node IDs, result/skip counts and CI
run/job URLs. Require zero new platform-specific skips. A missing CI result is a
pending gate, not equivalent to local success. See plan.md's reviewable ownership
matrix and WP03 T012 for the exact completion obligations.

```powershell
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/test_safe_commit_cmd.py
uv run --extra test pytest -q tests/tasks/test_planning_workflow_integration.py tests/tasks/test_check_prerequisites_surface_agreement.py
uv run --extra test pytest -q tests/architectural/test_mission_resolver_walker_gate.py tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py
uv run --extra test ruff check src/specify_cli/missions/operation_context.py src/specify_cli/cli/commands/agent/mission_check_prerequisites.py src/specify_cli/cli/commands/agent/mission_setup_plan.py src/specify_cli/cli/commands/decision.py src/specify_cli/cli/commands/spec_commit_cmd.py
uv run --extra test mypy --strict src/specify_cli/missions/operation_context.py src/specify_cli/cli/commands/agent/mission_check_prerequisites.py src/specify_cli/cli/commands/agent/mission_setup_plan.py src/specify_cli/cli/commands/decision.py src/specify_cli/cli/commands/spec_commit_cmd.py
uv run python -m compileall -q src/specify_cli
git diff --check
```

## Original-workflow canary

Run the candidate CLI from the ancestry Mission task worktree and execute the exact resolver-returned prerequisite command. It must return that Mission's absolute task-worktree directory and leave `C:\Users\Ruslan\spec-kitty` unchanged.

Do not install or replace the active Spec Kitty CLI during this Mission.
