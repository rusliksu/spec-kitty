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
- 2026-09-04 command-selector slice: the actual `agent action implement WP01
  --mission linked-worktree-prerequisite-resolution-01M1MFE9 --agent codex`
  initially refused the Mission handle. RED commit `2e8fc22e3` reproduces this
  through both pre-existing workflow/tasks selector helpers (4 failed).
  Both helpers now consult MissionOperationContext and pass a selected linked
  anchor to the canonical handle resolver; primary/legacy paths remain unchanged.
  Missing/ambiguous selectors and conflicting immutable identities are explicitly
  tested for both consumers. Selector suite: 10 passed. Existing tasks helper and
  move-task Git validation suites: 19 passed. Ruff, compileall and strict mypy
  pass; the latter includes tasks.py and core/subtask_rows.py so the repository's
  import-skip configuration does not erase existing helper return types.
- Live implement now passes selector resolution but still stops at
  `workflow_executor.implement_locate_wp`: its call has not yet adopted the
  effective-root/status projection added in the previous slice. The preceding
  branch banner still reports primary main. Thus this is NOT a restored workflow
  or a review handoff. Three WPs remain planned. The next recovery slice must
  propagate context through the executor and branch-context consumers while
  retaining dependency, ownership and commit gates; do not replace repo_root
  wholesale with the Mission anchor. No workspace or status transition occurred.
- 2026-09-04 executor pre-mutation recovery: RED `9c40def0f` pins the actual CLI
  reaching dependency refusal without workspace/status mutation. RED `da181b6cd`
  extends this to the exact linked analysis-report path; merely asserting
  analysis_report_required had initially missed a wrong-primary-path refusal.
  The implementation carries the validated anchor/status projection through
  branch context, WP lookup, dependency reads and feedback/analysis reads.
  Default callers retain existing behavior. Explicit-anchor read overrides are
  restricted to PRIMARY-partition kinds by the canonical predicate; explicit
  branch-context failures no longer degrade to a primary-branch fallback.
- Final verification: linked CLI pre-mutation scenarios 2 passed, 26 deselected;
  implement/programmatic-call/mixed-dependency and analysis-report-rehome suites
  26 passed. Ruff, strict mypy and compileall pass. Two adjacent tests had
  platform-specific path assumptions: workspace equality now uses Path, and the
  Git revision path in the review-cycle test uses as_posix (also making the
  negative git-show check meaningful on Windows). A temporary incorrect predicate
  import was caught during iteration and replaced with is_primary_artifact_kind;
  final tests were rerun after that correction.
- Live WP01 implement now reports the task branch and analysis_report_required
  for the actual task-owned Mission's analysis-report.md. That file is absent:
  the next legitimate step is /spec-kitty.analyze plus canonical record-analysis,
  not bypassing the gate. Post-analysis workspace allocation, claim persistence,
  tasks transitions and review are still unverified/unrecovered. All three WPs
  remain planned; primary is clean at 6befd9b43174b9f2c117f8bc02443001c9c25cb6.

### 2026-09-04 — analysis persistence and freshness recovery

- Audience: software-engineer / next Mission operator. Bead: `spk-1m6`.
- Live blocker: explicit `record-analysis --mission` returned
  `FEATURE_CONTEXT_UNRESOLVED` after primary re-anchoring; prerequisites already
  resolved the linked Mission correctly. Ruslan approved this bounded repair.
- RED `d51c7779b`: two actual CLI tests (slug and immutable ID) failed at
  selection. RED `c2a1adea6`: a valid linked report failed the implement gate with
  `path_relativization_failed`; refusal controls also pin pre-write safety.
- Reused `MissionOperationContext` plus existing `mission_context_for` artifact
  read/write/commit projections. Only recorder and its implement freshness caller
  changed; no new resolver or manual report writer. The owned root now reaches
  dirty preflight, report hash inputs, and the canonical commit router. Charter
  hashes still use the canonical charter root.
- Intermediate tests caught two further boundaries: hashing against primary and
  checking primary dirt instead of selected-worktree dirt. Both were corrected.
  Fixture `.gitignore` now mirrors the real repository's ignored sync-state file;
  report tracking and all primary byte/index/HEAD assertions remain strict.
- Final Windows tests: 9 linked persistence/freshness/refusal/implement-gate cases
  passed (26 unrelated cases deselected), plus 52 recorder/implement/rehome
  regressions passed. A post-record spec mutation invalidates freshness, proving
  source input values affect the gate. Original re-anchor behavior was caught by
  the committed RED tests. Ruff, strict mypy (5 explicit inputs), compileall and
  diff-check passed. POSIX CI was not run.
- No real Mission analysis verdict or WP transition was manufactured. Run fresh
  analyze and persist its actual findings next; WP01 is not approved and WP02
  must not start. No push, install, deployment or primary-checkout changes.
