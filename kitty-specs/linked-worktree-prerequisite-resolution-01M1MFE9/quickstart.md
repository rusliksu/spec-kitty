# Quickstart: Linked Worktree Prerequisite Resolution

## Isolation

```powershell
Set-Location C:\Users\Ruslan\.codex-worktrees\spec-kitty-check-prerequisites-task-worktree-resolution
git status --short --branch
```

Expected branch: `codex/check-prerequisites-task-worktree-resolution`.

## RED contract

```powershell
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/test_safe_commit_cmd.py -k "linked_worktree or owned_checkout"
```

The new tests must fail because the affected consumers re-anchor to primary, while existing operation-context tests remain green.

## GREEN and integration

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
