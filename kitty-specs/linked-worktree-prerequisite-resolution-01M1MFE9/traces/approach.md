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
- 2026-09-04 recovery implementation: WP lookup now receives the validated
  effective root and pre-resolved status directory; workspace metadata and lane
  manifest reads retain that anchor, while allocation/identity roots remain
  unchanged. The four committed lifecycle RED cases now pass (4 passed,
  12 deselected); the contract also asserts lane workspace paths stay under the
  repository-root `.worktrees` directory. Live implement-context for WP01 now
  succeeds with lane `planned`, lane_id `lane-a`, and the task-owned WP file.
- Closest regression set: `tests/tasks/test_tasks_support.py`,
  `tests/runtime/test_workspace_context_unit.py`,
  `tests/agent/test_context_resolve_unit.py`, and
  `tests/specify_cli/missions/test_operation_context.py`: 56 passed using a unique
  `--basetemp C:/Windows/Temp/spec-kitty-recovery-<uuid>` outside the user's
  `.kittify` ancestor. Initial default-temp execution had three root-discovery
  fixture failures caused by that ancestor and one POSIX-only path assertion.
  The latter now compares Path components; no product root-discovery behavior
  was changed. These failures were resolved, not waived as accepted baseline.
- Ruff passes on all five edited Python files. Strict mypy passes on the three
  edited source files plus `core/paths.py` and the linked-worktree test. Including
  `core/paths.py` avoids import-skip-induced Any diagnostics in unchanged
  find_repo_root code. Compileall and diff-check pass. This remains a context-read
  slice: workflow/task command execution and WP lifecycle advancement are pending.
- Checkout-identity and context invariant/parity suite:
  `tests/integration/test_wp_integrity_checkout_identity.py`,
  `tests/mission_runtime/test_context_factory_invariant.py`, and
  `tests/architectural/test_execution_context_parity.py`: 38 passed (200.32s).
  Total across the three focused runs: 98 passed. Primary checkout remains clean
  at `6befd9b43174b9f2c117f8bc02443001c9c25cb6`; no actual Mission transition,
  workspace allocation, push, installation or deployment was performed.
