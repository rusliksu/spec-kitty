# WP01 RED evidence — 2026-09-04

## Corrected status

The previous description of WP01 as complete was premature. The original test
coupled decision open and verify, so an open failure prevented verify from
running. Primary-cleanliness assertions after success assertions did not execute
on failed commands. The prerequisite branch contract was not asserted.

The corrected harness invokes each command independently and snapshots primary
HEAD, porcelain status, and file bytes before and after every CLI invocation,
including unsuccessful invocations. Decision open now supplies a required slot
key so a later successful resolver does not merely expose invalid test input.

## Verification

`uv run --extra test pytest -q tests/tasks/test_linked_worktree_planning_context.py`

Result: **5 failed, 7 passed**. The five failures reproduce remaining defects:

| Test | Observed RED |
|---|---|
| Prerequisite branch contract | current_branch is main instead of codex/task |
| Setup plan by immutable ID | PLAN_CONTEXT_UNRESOLVED |
| Decision open by immutable ID | FEATURE_CONTEXT_UNRESOLVED |
| Independent decision verify by slug | FEATURE_CONTEXT_UNRESOLVED |
| Spec commit in linked checkout | protected primary main selected |

Passing controls cover exact slug/ID prerequisite paths, conflicting immutable
identities in the shared resolver, missing/unsafe selectors, and omitted/ambiguous
selectors in a multi-Mission fixture. All per-command primary snapshots matched.

`.venv/Scripts/ruff.exe check tests/tasks/test_linked_worktree_planning_context.py`
passed with exit 0.

`.venv/Scripts/mypy.exe --strict --follow-imports=silent tests/tasks/test_linked_worktree_planning_context.py`
passed with exit 0.

These are RED authoring results, not Mission acceptance or WP approval. Windows
was exercised; POSIX CI remains pending. Full consumer-level conflict diagnostics
and context-emitted-command parity still need verification before closing WP01.

## Lifecycle recovery boundary

Canonical state still has WP01 planned. Existing action implement/context and
move-task failures must be repaired before recording a legitimate review handoff.
Do not fabricate lifecycle events or bypass dependency/branch-protection guards.

The earlier statement that this automatically belongs to WP02 was inaccurate:
WP02 currently owns prerequisites and setup-plan only. A recovery plan must name
the additional workflow consumers explicitly:

- `src/specify_cli/cli/commands/agent/workflow.py`: explicit Mission selection.
- `src/specify_cli/cli/commands/agent/tasks_shared.py`: move-task Mission selection.
- `src/mission_runtime/resolution.py`: WP-bearing context passes the repository
  root to work-package lookup after selecting a caller-owned Mission directory.

Keep this recovery separate from WP02 completion. Reuse operation context and
preserve distinct Git repository and Mission artifact authorities. Existing
bootstrap patches are provisional and require review against these invariants.
