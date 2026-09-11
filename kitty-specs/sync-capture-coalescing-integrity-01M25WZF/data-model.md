# Data Model: Sync Capture Coalescing Integrity

Mission: `sync-capture-coalescing-integrity-01M25WZF`

## Entities

**Journal entry** (`journal_entries`, one row per captured event identity)
- `entry_id` - the event identity; primary key component.
- `project_uuid` - owning project store.
- `epoch_id` - consent epoch the capture belongs to.
- `capture_sequence` - monotonic capture order inside the epoch.
- `payload_json` - the encoded event document (payload is base64 inside it).
- `created_at` - event creation time.

**Outbox task** (`outbox_tasks`, the delivery unit)
- `task_id` - `event:<identity>` for captures, `coalesce:<prior>:<new>` for supersede markers.
- `project_uuid`, `epoch_id` - same ownership tuple as the journal entry.
- `journal_entry_id` - the entry this task delivers. **Foreign key to
  `journal_entries(project_uuid, entry_id)`** - the invariant this mission repairs.
- `task_kind` - `event` or `coalesce_supersede`.
- `state` - `pending` for captures, `recorded` for supersede markers.
- `idempotency_identity`, `created_at` - retry metadata and ordering.

**Delivery attempt / result** (`delivery_attempts`, `delivery_results`)
- An attempt belongs to an entry and a target; a result records the terminal outcome.
- "Delivered anywhere" means a terminal-success attempt/result exists for the entry.
  Only that state makes a payload immutable.

**Coalesce key** (derived, not stored as a column)
- Produced by `_coalesce_key` from `COALESCEABLE_EVENT_TYPES`: project, mission slug and
  artifact path for `MissionDossierArtifactIndexed`; project and mission slug for
  `MissionDossierSnapshotComputed`. Any other event type yields no key.

**Unit of work** (`ProjectUnitOfWork`)
- The store-owned transaction a capture writes inside. The coalescing answer must be read
  from this transaction, never from a pinned one.

## Relationships

```
consent_epochs 1 --- n journal_entries 1 --- n outbox_tasks        (FK: project_uuid, epoch_id)
journal_entries 1 --- n outbox_tasks                               (FK: project_uuid, journal_entry_id)
journal_entries 1 --- n delivery_attempts 1 --- n delivery_results
```

## Capture decision state machine (A1)

```
capture(event)
  |
  |- event id already has a journal row           -> no-op, existing task is reused
  |- no coalesce key, or no candidate with the key-> store as new: journal row + outbox task
  |- candidate exists and is delivered anywhere   -> store as new + write supersede marker
  |- candidate exists and is undelivered          -> FOLD: replace the candidate payload,
  |                                                  write no new journal row,
  |                                                  write no new outbox task,
  |                                                  return success
  '- queue at cap                                 -> refuse without writing
```

## Invariants

- **I-1**: every `outbox_tasks` row with a non-null `journal_entry_id` references an
  existing journal entry of the same project (enforced by the composite foreign key).
- **I-2**: a fold never increases the pending task count and never changes the identity of
  the surviving entry.
- **I-3**: a delivered entry's stored payload bytes are unchanged by any later capture.
- **I-4**: `queue_size == persisted pending count` after every capture, including folds.
- **I-5**: a repeated capture of an already-captured identity is a no-op, not a new row.
