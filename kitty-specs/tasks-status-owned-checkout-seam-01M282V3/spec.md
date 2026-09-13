# Mission Specification: Task and status commands honour an owned checkout

**Mission Branch**: `codex/tasks-status-owned-checkout`
**Created**: 2026-09-11
**Status**: Draft
**Input**: User description: "let the task and status command families address a mission that lives in an owned linked worktree, so work-package lane transitions and review verdicts can be recorded from that checkout instead of failing with mission_not_found."

## Context

The agent surface can already work against an explicitly declared checkout: `spec-kitty next`,
`spec-kitty spec-commit` and `spec-kitty agent mission create` all accept `--owned-checkout`.
Every command that records work-package state does not, and resolves its mission census from the
project root, which by design collapses a linked worktree back to the primary checkout. The result is
a mission that can be created, planned and implemented through the owned checkout but whose lane
transitions and review verdicts cannot be recorded at all, so its runtime stops at `implement` with
`reason: "no actionable wp"`.

Reproduction and impact are recorded as issue 26
(<https://github.com/rusliksu/spec-kitty/issues/26>), with the friction trace on `main` at
`kitty-specs/sync-capture-coalescing-integrity-01M25WZF/traces/tooling-friction.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a lane transition from the owned checkout (Priority: P1)

An operator working in a mission's owned worktree moves a work package from `doing` to
`for_review` and then to `approved`. The command must address the mission in that checkout, write
the canonical status event into that checkout's mission surface, and leave the protected primary
checkout untouched.

**Why this priority**: without it no mission that uses an owned checkout can be reviewed, accepted or
closed, which is exactly the state the previous mission ended in.

**Independent Test**: from a real owned worktree of a `single_branch` mission, run the transition
command with the checkout declared and assert the event lands in that mission's status log with the
expected lane, while the primary checkout's HEAD, index and files are unchanged.

**Acceptance Scenarios**:

1. **Given** a mission whose directory exists only in an owned linked worktree, **When** a lane
   transition is issued with that checkout declared, **Then** the command succeeds and the canonical
   status event records the requested lane.
2. **Given** the same mission, **When** the same transition is issued without declaring a checkout,
   **Then** the command still fails closed with the existing `mission_not_found` diagnostic rather
   than guessing.

---

### User Story 2 - Record a review verdict from the owned checkout (Priority: P1)

The same operator approves a work package with a structured review result after reviewing it. The
verdict must be recorded through the canonical event seam for the mission in the owned checkout.

**Why this priority**: a review verdict is the gate that lets a mission advance, and today it cannot
be expressed at all from an owned worktree.

**Independent Test**: issue an approval with a structured review result from the owned worktree and
assert the status log carries the verdict for the right work package and lane.

**Acceptance Scenarios**:

1. **Given** a work package in `for_review` in an owned mission, **When** the approval is issued with
   the checkout declared and a review result, **Then** the canonical status log records the approval
   and the work package resolves to `approved`.
2. **Given** an invalid review result payload, **When** the approval is issued, **Then** the command
   refuses with a typed error and records nothing.

---

### User Story 3 - Planning-side commands stop writing into the protected primary (Priority: P2)

A planning-side command that cannot address an owned mission must say so instead of writing its
artifacts into the protected primary checkout.

**Why this priority**: during the previous mission the research scaffolder wrote four files into the
protected primary checkout and they had to be moved by hand and the primary cleaned; a refusal is
strictly safer than a silent misplacement.

**Independent Test**: run the planning-side commands from an owned worktree for a mission that lives
there and assert either success inside the owned checkout or a typed refusal, never a write into the
primary.

**Acceptance Scenarios**:

1. **Given** an owned mission, **When** a planning-side command that supports the seam runs, **Then**
   its artifacts appear inside the owned checkout.
2. **Given** an owned mission, **When** a planning-side command that does not support the seam runs,
   **Then** it refuses with an actionable message and the primary checkout proves unchanged.

### Edge Cases

- The declared path is the primary checkout itself: treated as the existing behaviour, not an error.
- The declared path is a directory that is not a worktree of the resolved primary: refused.
- The declared path is a worktree of a different repository: refused.
- The mission exists in both the primary and the owned checkout with divergent content: the declared
  checkout is authoritative and the divergence is reported, not silently resolved.
- The mission exists in neither: the existing `mission_not_found` diagnostic is preserved.
- A transition that is invalid for the state machine is refused for the owned mission exactly as it
  is for a primary mission.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Lane transitions address a declared owned checkout | As an operator, I want to move a work package between lanes with the checkout declared so that the transition is recorded for the right mission. | High | Open |
| FR-002 | Review verdicts address a declared owned checkout | As a reviewer, I want to approve or reject a work package through the canonical status seam with the checkout declared. | High | Open |
| FR-003 | The declared checkout is validated | As a maintainer, I want an unrelated or foreign path refused with a typed error so that a typo cannot redirect writes. | High | Open |
| FR-004 | Writes land in the declared checkout only | As an operator, I want the status log, snapshot and task checklist of the declared checkout updated while the protected primary stays byte-identical. | High | Open |
| FR-005 | Existing routing is unchanged without the declaration | As a maintainer, I want primary, coordination and lane routing to behave exactly as before when no checkout is declared. | High | Open |
| FR-006 | Planning-side commands never write into the primary for an owned mission | As an operator, I want such commands to succeed inside the owned checkout or refuse loudly, never to place artifacts in the protected primary. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|------|-------------|----------|----------|--------|
| NFR-001 | Reproduction from issue 26 passes end to end | The exact command sequence recorded in issue 26 must complete without `mission_not_found` for the mission in the owned worktree, with the resulting lane observable in the canonical status log. | Reliability | High | Open |
| NFR-002 | No silent inference | The checkout is honoured only when declared explicitly by the caller; no environment variable, working directory or heuristic may enable it implicitly. | Safety | High | Open |
| NFR-003 | Existing suites stay green | The task and status command suites, the architectural gates and the sync shard must pass at the candidate SHA on POSIX CI, with no new skip, xfail or deselection. | Quality | High | Open |
| NFR-004 | Primary checkout proof | Every acceptance run records the primary checkout's HEAD, cleanliness and unchanged file set before and after. | Safety | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Bounded blast radius | Only the task and status command families, their shared resolution seam and their tests may change. | Technical | High | Open |
| C-002 | No second writer | The canonical status event log stays the single authority; no new writer, table or side channel is introduced. | Technical | High | Open |
| C-003 | Protected primary untouched | No change may be committed or written to the protected primary checkout during planning or implementation. | Process | High | Open |
| C-004 | Complementary to the in-flight owned-context work | Pull request 20 carries deeper owned-mission routing for `move-task`; this mission must not conflict semantically with it, and where approaches differ the difference is recorded. | Process | Medium | Open |

### Key Entities

- **Owned checkout**: an explicitly declared repository root that may be the primary checkout or a
  validated linked worktree of it.
- **Mission census**: the set of missions discoverable under a checkout's `kitty-specs/`.
- **Lane transition**: the canonical status event that moves a work package between lanes.
- **Review result**: the structured verdict attached to a transition out of review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The issue-26 reproduction completes for a mission in an owned worktree: every command in
  it either succeeds with the expected observable state or fails with an actionable diagnostic, and
  none returns `mission_not_found` for a mission that exists in the declared checkout.
- **SC-002**: A lane transition and an approval issued from an owned worktree are visible in that
  mission's canonical status log, and its snapshot resolves the work package to the requested lane.
- **SC-003**: The protected primary checkout's HEAD and working tree are unchanged after every
  acceptance run.
- **SC-004**: With no checkout declared, the task and status command suites behave exactly as before.
- **SC-005**: POSIX CI is green at the candidate SHA for the affected suites and the architectural
  gates, with no new skip.
