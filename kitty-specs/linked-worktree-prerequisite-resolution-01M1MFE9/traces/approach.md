# Approach Trace

- `/spec-kitty.tasks` for `planning-artifact-ancestry-fix-01M1K666` reproduced `FEATURE_CONTEXT_UNRESOLVED` with an exact slug and immutable ID.
- `agent context resolve` succeeded for the same selector and task worktree.
- `setup-plan`, decision open/verify, and `spec-commit` reproduced primary-only resolution failures.
- Current `agent context resolve` already consumes `resolve_mission_operation_context()`; the failing commands do not.
- The repair therefore adopts that existing seam across the affected consumers with ATDD-first evidence and no global read-path rewrite.
- 2026-09-04: that earlier action-context success did not cover WP-bearing actions.
  Ruslan approved a lifecycle bootstrap extension in plan.md. The new real-Git
  `test_lifecycle_context_selects_linked_wp` covers implement/review by slug and
  immutable ID with a task file and canonical lanes manifest. All four cases
  reproduce WORK_PACKAGE_UNRESOLVED at the repository-root checkout, before
  workspace lookup can complete; the primary snapshot assertions all pass.
  Command: `.venv/Scripts/python.exe -m pytest -q tests/tasks/test_linked_worktree_planning_context.py -k lifecycle_context`.
  Result: 4 failed, 12 deselected (77.72s). These are intentional, in-scope RED
  reproductions, not an accepted unrelated failing baseline. Ruff, strict mypy,
  compileall and diff-check pass. The tests are committed before production
  changes per ATDD discipline. Context resolution is read-only: these tests do
  not yet demonstrate a successful implement/review transition or workspace
  allocation. Emitted-command execution and mutation guards remain recovery
  acceptance work; no WP is approved or advanced by this test package.
