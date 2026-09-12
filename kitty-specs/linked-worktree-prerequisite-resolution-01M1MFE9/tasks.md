# Tasks: Linked Worktree Prerequisite Resolution

**Mission**: `linked-worktree-prerequisite-resolution-01M1MFE9`
**Planning branch**: `codex/check-prerequisites-task-worktree-resolution`
**External merge target**: fork `main`
**Execution policy**: Sequential ATDD lane; no implementation begins until task finalization or an explicitly recorded bootstrap recovery decision.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Build a registered linked-worktree Mission fixture with primary cleanliness probes | WP01 | No |
| T002 | Drive harness invocation and snapshot acceptance RED-to-GREEN | WP01 | No |
| T003 | Preserve historical product RED evidence and map unchanged success assertions to WP02/WP03 | WP01 | No |
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
WP01 Verified Harness -> WP02 Read-Side Planning Consumers -> WP03 Decision and Commit Consumers
```

The packages are deliberately sequential. They share one authority contract and WP01's real-Git fixture; parallel implementation would risk divergent interpretations of caller-owned identity.

## WP01 — Verified Linked-Worktree Harness

**Prompt**: [tasks/WP01-linked-worktree-red-contract.md](tasks/WP01-linked-worktree-red-contract.md)
**Priority**: P1
**Dependencies**: None
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006
**Independent test**: Harness acceptance is RED before harness implementation and GREEN on the final WP01 commit; it proves registration, exact invocation and primary snapshots independently of unrepaired product consumers. Historical product RED remains evidence, not approval.
**Estimated prompt size**: ~240 lines

- [ ] T001 Build a registered linked-worktree Mission fixture with primary cleanliness probes (WP01)
- [ ] T002 Drive harness invocation and snapshot acceptance RED-to-GREEN (WP01)
- [ ] T003 Preserve historical product RED evidence and map unchanged success assertions to WP02/WP03 (WP01)
- [ ] T004 Pin missing, ambiguous, unsafe, conflicting-identity, and primary-clean controls (WP01)

**Implementation sketch**: Implement a reusable harness and its independently green acceptance suite in the two WP01-owned files. Preserve historical RED commits. Do not edit, suppress, or invert the existing mixed product contract; WP02 and WP03 close their own behavioral acceptance under the plan's reviewable test-ownership matrix.

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

**Implementation sketch**: First commit read-consumer acceptance RED in the owned consumer suites using WP01's harness. Consume `MissionOperationContext` at each command boundary, keep Git policy on `repository_root`, and resolve artifact paths/identity through `mission_anchor_root`. Require the complete WP02 suites GREEN before review; remove no guard and add no directory scan.

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

**Implementation sketch**: Commit write-consumer acceptance RED before fixes. Apply WP02's authority split, retain routers and protection checks, and reconcile the existing mixed integration contract without dropping any assertions. Require all focused suites GREEN, the original-workflow canary and same-SHA Windows/POSIX CI evidence before approval; no global candidate installation.

**Parallel opportunities**: None; write-path work follows the read-side pattern and closes the same sequential lane.

**Risks**: A permissive file-root check could write across Mission surfaces. Require selected-identity ownership and explicit primary-clean evidence.

## MVP Recommendation

WP01 is reviewable only when its harness acceptance is GREEN after committed RED evidence. It does not claim repaired planning consumers. The useful product fix requires WP01 and WP02; full scope and resumption require all three packages, complete green focused tests and NFR-001 evidence. No WP state changes are implied by this planning correction.
