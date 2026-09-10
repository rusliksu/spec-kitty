---
work_package_id: "WP01"
title: "Capture fold integrity"
dependencies: []
requirement_refs:
  - FR-001
  - FR-002
  - FR-003
  - FR-005
  - NFR-003
  - C-002
  - C-004
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
  - T006
owned_files:
  - "src/specify_cli/sync/queue.py"
  - "tests/sync/test_queue_resilience.py"
  - "tests/sync/test_offline_queue_counter.py"
authoritative_surface: "src/specify_cli/sync/"
execution_mode: "code_change"
---

# Work Package Prompt: WP01 – Capture fold integrity

## Objective

Make `OfflineQueue.queue_event` honour the journal coalescing seam's decision: when the
seam answers "not stored as new" (a fold), the capture must write no new journal entry and
no new outbox task, must leave the surviving undelivered entry's payload replaced, and must
report success. Today the capture path writes the outbox task anyway and the composite
foreign key refuses it.

## Context

**Why this exists.** The journal coalescing seam is process-global by design; a long-lived
hosted-sync process installs it during its first drain (`delivery/dispatcher.py`,
`_install_coalescing` / `_coalescing_query_for`). After that, a capture whose event
carries a coalesce key matching an undelivered journal entry is folded:
`EventJournal.append` returns a sentinel receipt (`capture_sequence=0`, `epoch_id=0`,
`inserted=False`) and writes no row for the incoming identity. `queue_event` ignores that
outcome and inserts `outbox_tasks(journal_entry_id = <incoming identity>)`; the schema
enforces `FOREIGN KEY (project_uuid, journal_entry_id) REFERENCES
journal_entries(project_uuid, entry_id)`, so the insert fails with
`sqlite3.IntegrityError: FOREIGN KEY constraint failed` at what is now
`src/specify_cli/sync/queue.py`.

**Approved decision.** D-001 in `spec.md` is resolved as **A1**: a coalesced capture folds
into the surviving entry (one pending row, replaced payload, no new task). A2 was rejected.

**Base.** `main` at `78c1e9ab1` already carries the resolver-based seam (FR-004) and the
platform-hermetic daemon oracle (FR-006). It also carries an autouse
`tests/sync/conftest.py` fixture `_reset_event_journal_coalescing_seam` that resets the
process-global seam around every sync test. **That fixture is isolation, not a repair:**
it means the sync shard can be green while this defect is untouched, so the acceptance test
below must drive the drain and the capture **inside one test body** — a test that relies on
seam leakage from another file will be reset out from under it.

**Read first**: `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/spec.md` (FR-001,
FR-002, FR-005, C-004), `plan.md` (IC-01, IC-02), `data-model.md` (invariants I-1..I-5),
`research.md` (RD-001..RD-005, D-7).

## Subtasks & Detailed Guidance

### Subtask T001 – RED: drain-then-capture acceptance

- **Purpose**: prove the defect with an executable oracle that the new conftest fixture
  cannot mask.
- **Steps**:
  1. In `tests/sync/test_queue_resilience.py` add an acceptance test (name it for the
     contract, e.g. `test_capture_after_drain_folds_without_orphan_outbox_task`).
  2. Inside the single test body: build the project store fixture already used by the
     module, call the real `dispatch(store=..., receiver=StubReceiver(), target=...,
     context=...)` once (this installs the seam with the store's own unit of work, exactly
     as production does), then capture two events with the SAME coalesce key through
     `OfflineQueue.queue_event` on a unit of work opened after the drain.
  3. Assert: no exception; exactly one pending row for that coalesce key; no
     `outbox_tasks` row whose `journal_entry_id` has no `journal_entries` row
     (`SELECT COUNT(*) FROM outbox_tasks t LEFT JOIN journal_entries j ON
     j.project_uuid = t.project_uuid AND j.entry_id = t.journal_entry_id WHERE
     j.entry_id IS NULL` must be 0); the surviving entry's payload equals the second
     event's payload.
  4. Run it on the current head and record the RED output verbatim (expected:
     `sqlite3.IntegrityError: FOREIGN KEY constraint failed`).
- **Files**: `tests/sync/test_queue_resilience.py` (add ~60 lines).
- **Validation**: the test fails before the production change and passes after it.
- **Parallel?**: No — T002 depends on this oracle.

### Subtask T002 – Capture honours the fold

- **Purpose**: remove the unconditional outbox write (FR-001, FR-002).
- **Steps**:
  1. In `src/specify_cli/sync/queue.py`, use the receipt returned by
     `EventJournal.append` (`receipt.inserted` plus the sentinel shape
     `capture_sequence == 0 and epoch_id == 0`) to distinguish three outcomes: stored as
     new, already stored under this identity (idempotent re-append), and folded into a
     surviving entry.
  2. For the folded outcome, skip the `outbox_tasks` insert and return `True`: the event
     was captured, its payload now lives in the surviving entry, and that entry already has
     a pending task.
  3. Do not touch the seam, the ledger, the schema, the supersede branch, or the cap check.
     Do not add a second query or transaction (NFR-003).
  4. Keep the write inside the existing `execute_write` permit for the store-as-new path.
- **Files**: `src/specify_cli/sync/queue.py` (small, local change around the capture write).
- **Validation**: T001 turns GREEN; `tests/sync/test_queue_resilience.py` and
  `tests/sync/test_offline_queue_counter.py` pass after T004/T005.
- **Parallel?**: No.

### Subtask T003 – Idempotency, cap and re-capture edges

- **Purpose**: close the edge cases R-1/R-2 in `research.md`.
- **Steps**:
  1. Capture the same identity twice after a fold: the second call is a no-op returning
     `True`, with no additional row and no exception.
  2. Capture while the queue is at its cap: the existing refusal (`False`) must be
     unchanged and must not write anything.
  3. Capture a folded identity and then drain: the drained payload must be the surviving
     entry's replaced payload, under the surviving identity.
- **Files**: `tests/sync/test_queue_resilience.py`.
- **Validation**: all three assertions pass; the cap test's existing expectation is
  untouched.
- **Parallel?**: No.

### Subtask T004 – Coalescing oracle alignment under A1

- **Purpose**: the module's own oracle must state the approved contract (C-004).
- **Steps**:
  1. `test_coalescing_updates_existing_row` currently asserts queue size 2 after the
     second same-key capture while its docstring says "keeping queue size at 1". Under A1
     the assertion moves to the surviving identity: one pending row, payload replaced, and
     the drained event is the survivor with the second payload.
  2. Update the docstring so the prose and the assertion agree, and keep the test driven
     through the real dispatch-installed seam (no mock seam).
- **Files**: `tests/sync/test_queue_resilience.py`.
- **Validation**: the rewritten test fails on a mutant that restores the unconditional
  insert and passes on the repair.
- **Parallel?**: No.

### Subtask T005 – Counter oracle alignment under A1

- **Purpose**: keep the row-count invariant honest under folding.
- **Steps**:
  1. `test_counter_unchanged_on_coalesce` and
     `test_invariant_size_equals_disk_after_mixed_operations` in
     `tests/sync/test_offline_queue_counter.py` assert two pending rows for one coalesce
     key. Move them to the A1 contract: one pending row for the key, and
     `queue.size() == persisted pending` at every step.
  2. Preserve the file's stated intent (the counter is read inside the store's unit of work;
     no cached counter beside a path).
- **Files**: `tests/sync/test_offline_queue_counter.py`.
- **Validation**: the file passes and the invariant helper
  `assert_invariant()` holds after the folded capture.
- **Parallel?**: No.

### Subtask T006 – Mutation check

- **Purpose**: prove the oracle bites (ATDD discipline; directive 034).
- **Steps**:
  1. Temporarily re-enable the unconditional outbox insert (one-line local mutation), run
     T001's acceptance test, and confirm it fails.
  2. Revert the mutation, re-run, confirm GREEN. Record both outputs for the WP activity
     log; do not commit the mutation.
- **Files**: none committed (mutation is transient).
- **Validation**: RED under mutation, GREEN after revert.
- **Parallel?**: No — runs last.

## Definition of Done

- T001's acceptance test exists, reproduced RED before the change (output recorded) and
  GREEN after it, with the drain and the capture in one test body.
- `src/specify_cli/sync/queue.py` writes an outbox task only for identities the journal
  actually stored; the fold path writes nothing and returns success.
- `tests/sync/test_queue_resilience.py`, `tests/sync/test_offline_queue_counter.py`,
  `tests/event_journal/` and `tests/delivery/` are green with
  `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this worktree.
- `ruff check` and `mypy` pass on the changed files; `git diff --check` is clean.
- No new skip, xfail or deselection is introduced (NFR-002).
- The invariant query for orphan outbox tasks returns 0 after the acceptance sequence.

## Risks

- **Masking by isolation**: the per-test seam reset can hide the defect; mitigated by T001's
  single-body drain+capture and by T006's mutation check.
- **Over-broad change**: the fold path must not become a second coalescing rule; the seam
  stays the only authority (RD-002, RD-005).
- **Idempotency regression**: the sentinel receipt also covers a repeated identical
  capture, which must stay a no-op with the existing task preserved.
- **Payload identity**: folding must replace the surviving entry's payload and must never
  touch an entry the ledger reports as delivered anywhere (RD-004).

## Reviewer Guidance

Focus on: (1) is the production change limited to the capture write, with no new query or
transaction; (2) does the acceptance test genuinely reproduce the drain-then-capture
sequence in one body rather than relying on cross-test leakage; (3) do the rewritten
oracles state the A1 contract rather than weakening it; (4) is the orphan-task invariant
asserted directly; (5) does the mutation check evidence exist. Reject any change that
relaxes the outbox foreign key or adds a second coalescing authority.
