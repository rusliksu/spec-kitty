# Research: Sync Capture Coalescing Integrity

Mission: `sync-capture-coalescing-integrity-01M25WZF` (software-dev, single_branch)
Branch: `codex/sync-capture-coalescing`
Date: 2026-09-10
Bead: `spk-2ag`

## Question

Does the journal's coalescing seam, once installed, leave the project store consistent on
the capture path — and if not, what is the smallest change that makes capture
integrity-safe without weakening the delivered-payload guarantee?

## Evidence base

**D-1 - the seam answered through a closed transaction.** POSIX `CI Quality` job
`102246597822` (run `34281328452`, base head `ddab065eb`) failed
`tests/sync/test_queue_resilience.py::TestEventCoalescing::test_coalescing_updates_existing_row`
with `ProjectStoreError: project unit of work is no longer active`, raised through
`queue.py:426 -> journal.py:175 -> coalesce.py:43 -> ledger.py:535 -> ledger.py:181 ->
transport_attempts.py:515 -> project_store.py:205`. The installed strategy held a
`SqliteDeliveryLedger` pinned to the drain's unit of work, which closes with the drain.

**D-2 - reproducible in one process.** Running
`tests/delivery/test_dispatcher.py` together with the two queue nodes reproduces
`2 failed, 37 passed` on the unfixed base. Repair `a98f2cb54` makes the seam carry a
resolver (`journal -> DeliveredAnywhereQuery`) and the same selection passes.

**D-3 - the next defect is a foreign-key violation.** With the seam repaired, POSIX job
`102913159263` (run `34489743886`, head `342f784c7`) reports `3 failed, 3040 passed`:
the same three queue nodes now fail with `sqlite3.IntegrityError: FOREIGN KEY constraint
failed` raised at `sync/queue.py:433`.

**D-4 - the mechanism.** `EventJournal.append` returns a sentinel receipt with
`capture_sequence=0, epoch_id=0, inserted=False` when the active strategy answers
`store_as_new=False` (`journal.py:191-202`); it deliberately writes no row for the incoming
identity. `OfflineQueue.queue_event` ignores that outcome and unconditionally inserts
`outbox_tasks(journal_entry_id = event_id)` for the same identity (`queue.py:431-452`).
The schema enforces `FOREIGN KEY (project_uuid, journal_entry_id) REFERENCES
journal_entries(project_uuid, entry_id)` (`project_store.py:337`), so the insert is
refused — correctly. The database is protecting the invariant the capture path violates.

**D-5 - blast radius.** `EventJournal.append` has exactly one live caller in `src/`:
`sync/queue.py:426`. Every other `EventJournal(...)` site reads (`count`, `read_all`,
`read_by_id`, payload archiving) or is the migration import path
(`sync/migrate_journal.py` writes through its own staging transaction, not through the
coalescing seam).

**D-6 - which captures are coalescible.** `COALESCEABLE_EVENT_TYPES` (`queue.py:287`)
covers `MissionDossierArtifactIndexed` (project, mission slug, artifact path) and
`MissionDossierSnapshotComputed` (project, mission slug). Every other event type carries
`coalesce_key=None` and always stores as new.

**D-7 - the base moved during planning.** Pull request 24 was merged into `main` as
`78c1e9ab1`, together with `a84b110a7`, which adds an autouse `tests/sync/conftest.py`
fixture resetting the process-global coalescing seam around every sync test.
Consequence: the POSIX sync shard can now be green while the capture-path defect is
untouched, because no dispatcher-installed seam survives into a queue test. A test that
relied on leakage from an earlier file would be defeated by that fixture, and a green
shard alone is therefore not evidence that FR-001/FR-002 hold: the acceptance test must
perform the drain and the capture inside the same test body.

## Decisions

**RD-001 - capture folds into the surviving entry (A1, owner-approved 2026-09-10).**
A `store_as_new=False` decision must mean: no new journal row, no new outbox task, the
surviving undelivered entry's payload replaced in place, and an unchanged pending count.
Rationale: it is the journal's documented latest-wins contract, it is what the seam was
built to express, and A2 would leave a production process (one that has drained at least
once) unable to fold an undelivered duplicate at all. Accepted cost: the two fork oracles
that assert two pending rows for one coalesce key become stale and are updated under
C-004.

**RD-002 - the quota of authority stays with the database.** The repair does not relax,
drop or bypass the `outbox_tasks` foreign key; the capture path must stop violating it.
Enforcement stays where it already is.

**RD-003 - the seam keeps carrying a resolver, not an instance.** Repair `a98f2cb54`
already establishes this; the remaining work must not reintroduce a pinned unit of work,
ledger or connection (NFR-003).

**RD-004 - delivered payloads stay immutable.** The coalesced path may only touch entries
the delivery ledger has not delivered anywhere; the supersede path must keep writing a
marker instead of mutating the delivered entry (FR-003).

**RD-005 - no new capture path.** The fix lands in the single existing capture path; no
second writer, no command-local scan, no new table.

## Impact analysis

- `src/specify_cli/sync/queue.py` - the only production change: honour the journal's
  decision instead of unconditionally inserting an outbox task.
- `tests/sync/test_queue_resilience.py` - the coalescing oracle moves from two pending
  rows to one surviving identity, and the drain expectation follows the surviving entry
  (C-004 update, deliberate and recorded).
- `tests/sync/test_offline_queue_counter.py` - the counter oracle for one coalesce key
  moves from two rows to one.
- Unchanged: the journal seam contract, the delivery ledger, the schema, the dispatcher,
  the daemon, and the existing `a98f2cb54` / `342f784c7` repairs.

## Open questions and risks

- **R-1**: a coalesced capture returns success while the new identity never becomes a
  row. The queue must still be idempotent for a repeated capture of that identity, and the
  drained payload must be the surviving entry's replaced payload. Pinned by an acceptance
  test in the implementation package.
- **R-2**: the pending counter is read from `outbox_tasks`; after a fold it must not
  change. Pinned by the counter invariant test.
- **R-3**: the supersede branch (prior entry already delivered) still stores the new
  identity as a new row and must keep the delivered payload byte-identical. Existing
  journal tests already pin this; the implementation package must not disturb it.
- **R-4**: CI evidence for this mission must come from the same candidate SHA on POSIX and
  on native Windows, with the documented Windows-only baselines listed separately
  (NFR-001, NFR-002).

## Sources

See `research/source-register.csv` and `research/evidence-log.csv`.
