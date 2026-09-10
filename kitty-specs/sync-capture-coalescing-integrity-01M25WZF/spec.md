# Mission Specification: Sync Capture Coalescing Integrity

**Mission Branch**: `codex/sync-capture-coalescing`
**Created**: 2026-09-10
**Status**: Draft
**Input**: User description: "make hosted-sync capture-time coalescing integrity-safe end to end: the journal coalescing seam must never leave the project-store outbox or journal inconsistent, on any capture path and in any process that has already drained once."

## Context

Hosted sync captures events into a project-store journal and fans them out through an
outbox. A coalescing seam on the journal decides, for an event that carries a
`coalesce_key`, whether the event is stored as a new journal entry or folded into an
existing undelivered entry. The seam is process-global, while the project unit of work
that answers "delivered anywhere?" is not.

Two defects were proven on this branch's base (`main` at `ddab065eb`) and are already
repaired here; the remaining work is the capture-path integrity contract and its
verification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture after a drain stays integrity-safe (Priority: P1)

A long-lived hosted-sync process drains its journal once and then captures more events.
When a later captured event carries a coalesce key that matches an entry already in the
journal, the capture must never fail and must never leave the project store in a state
where an outbox task points at a journal entry that does not exist.

**Why this priority**: This is a data-integrity failure on the primary capture path.
Without it, hosted sync either loses events or corrupts the outbox after the first drain
in any daemon-like process.

**Independent Test**: In one process, drain once through the delivery dispatcher, then
capture two events with the same coalesce key and assert journal rows, outbox tasks and
queue size agree, with no exception raised.

**Acceptance Scenarios**:

1. **Given** a process that already completed one drain, **When** an event with a
   coalesce key matching an undelivered journal entry is captured, **Then** the capture
   succeeds and the project store holds no outbox task whose journal entry is missing.
2. **Given** the same process, **When** an event with a coalesce key whose prior entry is
   already delivered is captured, **Then** the capture succeeds, a supersede record links
   prior to new, and the delivered payload is byte-for-byte unchanged.

---

### User Story 2 - One coherent coalescing contract (Priority: P2)

The journal seam's decision is authoritative and every capture path honors it, so queue
size, persisted pending rows and journal rows always describe the same state.

**Why this priority**: Two capture oracles in the repository currently disagree about how
many pending rows a coalesced capture leaves behind, which means one of them encodes
behavior the product does not intend.

**Independent Test**: Drive the queue through same-key, different-key, duplicate-id and
cap-overflow sequences and assert the observable row counts agree at every step.

**Acceptance Scenarios**:

1. **Given** a capture path that receives a "not stored as new" decision, **When** the
   capture completes, **Then** no orphan task row is created and the reported queue size
   equals the persisted pending count.
2. **Given** a capture path with no coalescing seam installed, **When** an event is
   captured, **Then** the observed behavior matches the chosen contract in
   "Open Product Decisions" below.

---

### User Story 3 - Verifiable sync baseline on Windows and POSIX (Priority: P3)

The sync shard runs green at one candidate SHA on both native Windows and POSIX CI, so
the release gate can distinguish this repair from unrelated platform baselines.

**Why this priority**: The residual red gate is the only thing blocking the dependent
mission's WP03 acceptance; unverifiable green claims are not acceptable evidence.

**Independent Test**: Run the sync selection locally on Windows and observe the same
candidate SHA pass the POSIX `fast-tests-sync` job.

**Acceptance Scenarios**:

1. **Given** candidate SHA X, **When** the POSIX sync job runs, **Then** it reports zero
   failures and the aggregate quality gate reports no blocking verdict.
2. **Given** the same SHA, **When** the sync selection runs on native Windows, **Then**
   it reports the same node outcomes, allowing only documented platform baselines.

### Edge Cases

- An event is captured while the queue is at its cap: capture refuses without writing.
- The same event identity is captured twice: the second capture is a no-op, not a new row.
- A coalesce key exists but the journal has no candidate yet: the event is stored as new.
- The seam is installed by a drain whose unit of work has already closed.
- Two queue instances share one project store and capture interleaved events.
- A supersede record is written for a delivered prior entry: the prior payload must not
  change and a new row must exist for the new identity.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Honor the coalescing decision on every capture path | As a hosted-sync user, I want a "do not store as new" decision to be respected by the capturing path so that no orphan rows are written. | High | Open |
| FR-002 | No outbox task without its journal entry | As a hosted-sync user, I want the project store to reject or avoid any outbox row whose journal entry is missing, so that the outbox can always be drained. | High | Open |
| FR-003 | Latest-wins coalescing without mutating delivered payloads | As a hosted-sync user, I want an undelivered entry's payload replaced in place and a delivered entry left byte-identical, so that no acknowledged content changes. | High | Open |
| FR-004 | Seam stays usable after the installing drain closes | As a hosted-sync operator, I want capture to keep working after a drain has run, so that a long-lived process does not break on its second capture cycle. | High | Open |
| FR-005 | Row-count agreement after every capture | As a maintainer, I want queue size and persisted pending rows to agree after coalesced, superseding and duplicate captures. | Medium | Open |
| FR-006 | Daemon owner record describes the capturing environment | As an operator, I want the daemon's reported owner record to match the target this process resolves, so that health output is trustworthy. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|------|-------------|----------|----------|--------|
| NFR-001 | Same-SHA sync shard green on both platforms | The complete sync selection must report zero failures at one candidate SHA on POSIX CI and on native Windows, with only documented platform baselines excluded. | Reliability | High | Open |
| NFR-002 | No new skips or xfails | The repair must not add, widen or newly rely on any skip, xfail or deselection. | Quality | High | Open |
| NFR-003 | No additional database connection or transaction | Answering the coalescing query must reuse the appending unit of work; it must not open a connection, transaction or reader of its own. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Bounded blast radius | Only the journal coalescing seam, the capture path that consumes it, and the tests that pin them may change. | Technical | High | Open |
| C-002 | Process-global seam, unit-of-work-scoped answer | The seam may not pin a unit of work, ledger instance or connection across calls. | Technical | High | Open |
| C-003 | Protected primary stays untouched | Work happens on the mission branch; the protected primary checkout is not modified. | Process | High | Open |
| C-004 | Fork oracles are authoritative until changed explicitly | A test whose expectation contradicts the chosen capture semantics must be updated deliberately in this mission, never silently. | Process | Medium | Open |

### Key Entities

- **Journal entry**: a captured event owned by one project store, with an epoch, a
  capture sequence, a payload and an optional coalesce key.
- **Outbox task**: the delivery unit for a journal entry; it references the entry and
  cannot exist without it.
- **Coalesce key**: the value that makes two captures "the same latest value"; its
  presence is what makes a capture coalescible.
- **Delivery attempt / result**: the record that makes an entry "delivered anywhere",
  which is the only state that makes a payload immutable.
- **Unit of work**: the store-owned transaction that a capture writes inside and that the
  coalescing answer must be read from.

## Open Product Decisions

**D-001 (blocking for plan): what does a coalesced capture leave behind?**

- **Decision A1 - capture folds into the surviving entry.** A "not stored as new"
  decision means the capture writes no new journal entry and no new outbox task; the
  surviving undelivered entry's payload is replaced. Observable result: pending count
  unchanged, one row for the coalesce key.
- **Decision A2 - capture always stores a new entry.** Capture never folds; coalescing is
  expressed only through supersede records written for already-delivered entries.
  Observable result: pending count grows by one per capture.

Both decisions satisfy FR-001 and FR-002; they differ in what users observe and in which
fork test oracles remain valid. A1 matches the journal's documented latest-wins contract
and the queue test whose prose already says "keeps queue size at 1". A2 matches the
assertions currently written in the queue and counter suites.

**Status**: Open. Requires explicit owner approval before plan.

## Baseline Already On This Branch

- `a98f2cb54` - the coalescing seam carries a resolver and answers through the appending
  unit of work (FR-004), with a regression test that drains first and captures second.
- `342f784c7` - the daemon isolation oracle is platform- and scope-hermetic (FR-006).
- Published evidence: draft pull request 24 at these two commits; POSIX sync job moved
  from 4 failed / 3039 passed to 3 failed / 3040 passed, and the three remaining failures
  are the capture-path integrity defect this mission exists to close.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A drain-then-capture sequence in one process completes with zero exceptions
  and zero outbox tasks whose journal entry is missing.
- **SC-002**: The POSIX sync job reports zero failures and the aggregate quality gate
  reports no blocking verdict at the mission's candidate SHA.
- **SC-003**: After coalesced, superseding and duplicate captures, the reported queue size
  equals the persisted pending count in every asserted step.
- **SC-004**: A delivered entry's stored payload bytes are identical before and after any
  subsequent capture with the same coalesce key.
- **SC-005**: The native Windows sync selection reproduces the POSIX outcomes at the same
  SHA, allowing only documented platform baselines, with no new skips.
