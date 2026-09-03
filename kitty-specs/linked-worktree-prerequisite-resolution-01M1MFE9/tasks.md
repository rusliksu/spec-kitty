# Tasks: Linked Worktree Prerequisite Resolution

**Mission**: `linked-worktree-prerequisite-resolution-01M1MFE9`
**Planning branch**: `codex/check-prerequisites-task-worktree-resolution`
**External merge target**: fork `main`
**Execution policy**: Sequential ATDD lane; no implementation begins until task finalization or an explicitly recorded bootstrap recovery decision.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Build a registered linked-worktree Mission fixture with primary cleanliness probes | WP01 | No |
| T002 | Add RED prerequisites and setup-plan contract cases for slug and immutable ID | WP01 | No |
| T003 | Add RED decision and spec-commit contract cases on the same owned Mission | WP01 | No |
| T004 | Pin missing, ambiguous, unsafe, conflicting-identity, and primary-clean controls | WP01 | No |
| T005 | Route check-prerequisites through the canonical Mission operation context | WP02 | No |
| T006 | Route setup-plan through the same repository-root/mission-anchor split | WP02 | No |
| T007 | Extend focused unit coverage for both read-side consumers | WP02 | No |
| T008 | Make the shared RED contract green for prerequisite and plan setup paths | WP02 | No |
| T009 | Route decision open/verify through canonical operation context | WP03 | No |
| T010 | Route spec-commit validation and placement through canonical operation context | WP03 | No |
| T011 | Extend decision and commit-router regression coverage | WP03 | No |
| T012 | Run the original ancestry-Mission canary and the full quality gate | WP03 | No |

## Dependency Graph

```text
WP01 RED Contract Harness -> WP02 Read-Side Planning Consumers -> WP03 Decision and Commit Consumers
```

The packages are deliberately sequential. They share one authority contract and WP01's real-Git fixture; parallel implementation would risk divergent interpretations of caller-owned identity.

## WP01 — Linked-Worktree RED Contract Harness

**Prompt**: [tasks/WP01-linked-worktree-red-contract.md](tasks/WP01-linked-worktree-red-contract.md)
**Priority**: P1
**Dependencies**: None
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006
**Independent test**: On the planning base, the new exact-selector cases fail specifically because affected consumers re-anchor to primary, while existing operation-context controls remain green.
**Estimated prompt size**: ~240 lines

- [ ] T001 Build a registered linked-worktree Mission fixture with primary cleanliness probes (WP01)
- [ ] T002 Add RED prerequisites and setup-plan contract cases for slug and immutable ID (WP01)
- [ ] T003 Add RED decision and spec-commit contract cases on the same owned Mission (WP01)
- [ ] T004 Pin missing, ambiguous, unsafe, conflicting-identity, and primary-clean controls (WP01)

**Implementation sketch**: Create one integration contract file that invokes real command surfaces against a temporary primary repository and registered linked worktree. Capture exact RED reasons and commit them before production changes.

**Parallel opportunities**: None within the WP; fixture and assertions form one executable contract.

**Risks**: A mock-heavy fixture could pass without reproducing root re-anchoring. Require real Git worktree registration and before/after primary snapshots.

## WP02 — Read-Side Planning Consumer Adoption

**Prompt**: [tasks/WP02-read-side-planning-consumers.md](tasks/WP02-read-side-planning-consumers.md)
**Priority**: P1
**Dependencies**: WP01
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006
**Independent test**: `check-prerequisites` and `setup-plan` resolve the caller-owned Mission by slug and immutable ID, while all fail-closed controls remain unchanged.
**Estimated prompt size**: ~260 lines

- [ ] T005 Route check-prerequisites through the canonical Mission operation context (WP02)
- [ ] T006 Route setup-plan through the same repository-root/mission-anchor split (WP02)
- [ ] T007 Extend focused unit coverage for both read-side consumers (WP02)
- [ ] T008 Make the shared RED contract green for prerequisite and plan setup paths (WP02)

**Implementation sketch**: Consume `MissionOperationContext` at each command boundary, keep Git preflight on `repository_root`, and resolve artifact paths/identity through `mission_anchor_root`. Remove no guard and add no directory scan.

**Parallel opportunities**: None; WP02 is the first production adoption and establishes the calling pattern for WP03.

**Risks**: Passing the anchor as the repository root could corrupt topology semantics. Review the two authorities separately in every call.

## WP03 — Decision, Commit, and Workflow Closure

**Prompt**: [tasks/WP03-decision-commit-workflow-closure.md](tasks/WP03-decision-commit-workflow-closure.md)
**Priority**: P1
**Dependencies**: WP02
**Requirement refs**: FR-002, FR-003, FR-004, FR-005, FR-006
**Independent test**: Decision open/verify and spec-commit operate on the same caller-owned Mission, then the original ancestry Mission's exact tasks prerequisite command succeeds without primary changes.
**Estimated prompt size**: ~270 lines

- [ ] T009 Route decision open/verify through canonical operation context (WP03)
- [ ] T010 Route spec-commit validation and placement through canonical operation context (WP03)
- [ ] T011 Extend decision and commit-router regression coverage (WP03)
- [ ] T012 Run the original ancestry-Mission canary and the full quality gate (WP03)

**Implementation sketch**: Apply WP02's authority split to the write-capable consumers, retain their existing routers and protection checks, then prove end-to-end recovery using the blocked Mission without installing the candidate globally.

**Parallel opportunities**: None; write-path work follows the read-side pattern and closes the same sequential lane.

**Risks**: A permissive file-root check could write across Mission surfaces. Require selected-identity ownership and explicit primary-clean evidence.

## MVP Recommendation

WP01 is the minimum reviewable checkpoint because it produces trustworthy RED evidence. The useful product fix requires WP01 and WP02; full user-confirmed scope and resumption of the original Mission require all three packages.
