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

## 2026-09-04 prerequisite branch repair

The existing caller-branch RED now passes: check-prerequisites reads the branch
from `MissionOperationContext.mission_anchor_root` for an explicit selector.
Git preflight retains the canonical repository root; omitted-selector behavior
is unchanged. The nearby SPECS_DIR unit assertion now uses native Path rendering
instead of assuming POSIX separators on Windows.

Focused verification:

```text
.venv/Scripts/python.exe -m pytest -q tests/tasks/test_linked_worktree_planning_context.py -k prerequisites tests/tasks/test_check_prerequisites_surface_agreement.py tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
36 passed, 9 deselected
```

Ruff passes for both edited Python files. Strict mypy passes when checking
`mission_check_prerequisites.py` together with `mission_metadata.py`. A one-file
check reported two no-any-return errors in unchanged metadata wrappers because
the repository configuration skips specify_cli imports; explicitly including the
typed metadata source resolves those diagnostics without casts or suppressions.

Live candidate CLI canary returns valid=true, current_branch and target_branch
both `codex/check-prerequisites-task-worktree-resolution`, and
branch_matches_target=true. Primary remains clean at
`6befd9b43174b9f2c117f8bc02443001c9c25cb6`.

This bounded repair does not close WP01 or WP02. The full RED suite was not rerun;
setup-plan, decision open/verify, spec-commit and lifecycle recovery remain open.
WP-bearing context recovery also traverses `task_utils/support.py` and
`workspace/context.py`, so changing only the argument in runtime resolution is
insufficient. No lifecycle transition, push, PR, or installation was performed.
