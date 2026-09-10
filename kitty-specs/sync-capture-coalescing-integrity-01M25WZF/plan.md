# Implementation Plan: Sync Capture Coalescing Integrity

Mission: `sync-capture-coalescing-integrity-01M25WZF` | Bead: `spk-2ag` | Type: software-dev | Topology: single_branch

## Summary

The journal's coalescing seam is process-global and answers `store_as_new=False` for an
event whose coalesce key matches an undelivered journal entry. The single live capture
path (`OfflineQueue.queue_event`) ignores that answer and still inserts an
`outbox_tasks` row for the incoming identity, which the composite foreign key refuses.
The repair makes the capture path honour the seam's decision under approved decision
A1: a fold writes no new journal row and no new outbox task, the surviving undelivered
entry's payload is replaced, and the pending count is unchanged.

## Branch Contract

- Work surface: `codex/sync-capture-coalescing` in the owned worktree
  `C:\Users\Ruslan\.codex-worktrees\spec-kitty-sync-capture-coalescing`.
- Planning artifacts land on the same branch (single_branch topology, verified through
  `spec-kitty spec-commit --owned-checkout`).
- Base: `main` at `78c1e9ab1` (merge of pull request 24), which already contains the
  resolver-based seam, the daemon oracle repair and the per-test seam reset.
- Delivery: a new pull request from this mission branch to `main`; pull request 24 is
  merged and is no longer a delivery surface.
- The per-test seam reset in `tests/sync/conftest.py` is an isolation measure, not a
  repair: the WP01 acceptance test must drive the drain and the capture in one test.
- The protected primary checkout `C:\Users\Ruslan\spec-kitty` is never modified (C-003).

## Technical Context

- Language/runtime: Python 3.11+ (repository sources under `src/specify_cli`).
- Relevant modules: `src/specify_cli/sync/queue.py` (capture), `src/specify_cli/event_journal/journal.py`
  (seam contract), `src/specify_cli/delivery/dispatcher.py` (seam installer),
  `src/specify_cli/sync/project_store.py` (schema and unit of work).
- Test entry points: `tests/sync/` (capture and queue suites), `tests/event_journal/`,
  `tests/delivery/`, `tests/architectural/test_no_dead_symbols.py`.
- Hosted sync in tests is gated by `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; without it the sync
  suites collect as skipped, which is a false green and must be recorded as such.
- Windows note: `sync/transport_lease.py` imports `fcntl` unconditionally on this base, so
  a native Windows run needs the documented local import shim; POSIX CI does not.
- Static gates: `ruff`, `mypy`, `compileall`, `git diff --check`, plus the repository's
  architectural gates for the touched packages.

## Constitution Check

Charter is present for this project; the plan is written against the directives injected
for this mission.

- **024 locality of change / 025 boy-scout**: one production module changes; the seam
  contract and schema stay untouched (RD-002, RD-005).
- **030 test-and-typecheck quality gate / 034 test-first**: the capturing defect gets a
  failing acceptance test first, then the repair; ruff and mypy run on the changed files.
- **033 targeted staging / 045 PRs-only**: only mission files are committed, through
  `spec-commit` and a single task branch; delivery stays on draft pull request 24.
- **043 close the defect class by construction**: the repair removes the ability of the
  capture path to write a task without its entry, rather than special-casing one test.
- **044 canonical sources**: the journal's decision is the single authority; no second
  coalescing rule is introduced in the queue.
- **010 specification fidelity / 003 decision documentation**: the approved decision A1 is
  recorded in `spec.md` and in this plan; the oracles it supersedes are named explicitly.

No conflict found; no exception requested.

## Architecture

```
capture(event)
   |
   v
OfflineQueue.queue_event                       (src/specify_cli/sync/queue.py)
   |  builds Event with coalesce_key = _coalesce_key(event)
   v
EventJournal.append                            (src/specify_cli/event_journal/journal.py)
   |  _active_coalesce_strategy(journal, event)
   |     -> CoalescingStrategy.query_for(journal)   (resolver, repair a98f2cb54)
   |     -> SqliteDeliveryLedger(journal.unit_of_work, ...).delivered_anywhere(...)
   |
   +-- store_as_new=True  -> INSERT journal_entries, receipt.inserted=True
   +-- store_as_new=False -> NO row for the incoming identity; sentinel receipt
   |
   v
outbox task write                              (same module, execute_write)
   +-- A1 (this mission): skip when the seam folded the event
   +-- current base: unconditional INSERT -> FK (project_uuid, journal_entry_id)
```

The single behavioural rule added: the capture path may write an outbox task only for an
identity that the journal actually stored (or already had). Everything else — the seam,
the ledger query, the schema, the supersede branch — is unchanged.

## Project Structure

### Documentation (this mission)

- `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/spec.md` — approved requirements and decision A1.
- `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/research.md` + `research/` — evidence base.
- `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/data-model.md` — entities and invariants.
- `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/plan.md` — this plan.
- `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/tasks/` — work packages (next step).

### Source Code (repository root)

- `src/specify_cli/sync/queue.py` — the only production change.
- `tests/sync/test_queue_resilience.py` — coalescing oracle updated to the A1 contract.
- `tests/sync/test_offline_queue_counter.py` — counter oracle updated to the A1 contract.
- `tests/sync/test_daemon_project_isolation.py` — already repaired by `342f784c7`; not touched again.

## Implementation Concern Map

### IC-01 — Capture honours the fold (FR-001, FR-002, FR-005)

Acceptance first: a test that drains once through the delivery dispatcher and then
captures two same-key events in the same process, asserting no exception, no outbox task
without its journal entry, and an unchanged pending count. Then the production change:
the capture path skips the outbox write when the journal's receipt shows the incoming
identity was folded, and reports success for it. Idempotency for a repeated capture of a
folded identity is pinned separately (R-1).

### IC-02 — Oracle alignment under C-004 (FR-003, FR-005)

The queue and counter oracles currently assert two pending rows for one coalesce key.
Under A1 they are updated deliberately: one surviving identity, the replaced payload, and
the drain expectation following the surviving entry. The delivered-payload immutability
path (supersede marker, new row) keeps its existing assertions and gains no exception.

### IC-03 — Verifiable baseline on both platforms (NFR-001, NFR-002, NFR-003)

Local: the sync selection on native Windows with the documented import shim, recording
interpreter, candidate SHA and exact node counts. Cloud: the POSIX `fast-tests-sync` job
and the aggregate quality gate at the same candidate SHA. No new skip, xfail or
deselection may be introduced, and the plan forbids adding a connection or transaction to
answer the coalescing query.

## Verification Strategy

1. RED: the IC-01 acceptance test fails on the current head with
   `sqlite3.IntegrityError: FOREIGN KEY constraint failed` at `sync/queue.py:433`.
2. GREEN: after the repair, the same test passes, and
   `tests/sync/test_queue_resilience.py`, `tests/sync/test_offline_queue_counter.py`,
   `tests/delivery/`, `tests/event_journal/` and the dead-symbol gate are green.
3. Static: `ruff check`, `mypy` on changed modules, `compileall`, `git diff --check`.
4. Cloud: push the candidate and read the POSIX `fast-tests-sync` job; the mission's
   acceptance requires zero failures there and no blocking quality-gate verdict.
5. Negative control: a mutant that re-enables the unconditional outbox insert must be
   caught by the IC-01 acceptance test.

## Complexity Tracking

No constitutional exception is requested. The change adds no abstraction, no new module,
no new table and no new capture path; it removes one unconditional write.

## Parallel Work Analysis

### Dependency Graph

```
IC-01 (capture repair + acceptance)  ->  IC-02 (oracle alignment)  ->  IC-03 (both-platform evidence)
```

### Work Distribution

The three concerns are strictly sequential: IC-02 can only be settled once the capture
behaviour is fixed, and IC-03 only once the oracles are green. This mission therefore
plans two work packages: one for IC-01 + IC-02 (code and oracles together, because the
oracles are the executable statement of the new contract), and one for IC-03 (evidence
and CI closure). Single-branch topology keeps both on the mission branch.

### Coordination Points

- The candidate SHA for the cloud evidence must be the same SHA the local evidence names.
- The dependent mission `linked-worktree-prerequisite-resolution-01M1MFE9` (WP03/T012)
  reads this mission's result; its residual gate is closed only when this shard is green
  on the base, so the evidence must be published, not merely local.
