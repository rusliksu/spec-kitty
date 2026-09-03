# Approach Trace

- `/spec-kitty.tasks` for `planning-artifact-ancestry-fix-01M1K666` reproduced `FEATURE_CONTEXT_UNRESOLVED` with an exact slug and immutable ID.
- `agent context resolve` succeeded for the same selector and task worktree.
- `setup-plan`, decision open/verify, and `spec-commit` reproduced primary-only resolution failures.
- Current `agent context resolve` already consumes `resolve_mission_operation_context()`; the failing commands do not.
- The repair therefore adopts that existing seam across the affected consumers with ATDD-first evidence and no global read-path rewrite.
