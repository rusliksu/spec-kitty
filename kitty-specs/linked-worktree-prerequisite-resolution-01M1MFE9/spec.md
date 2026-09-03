# Mission Specification: Linked Worktree Prerequisite Resolution

**Mission Branch**: `codex/check-prerequisites-task-worktree-resolution`
**Created**: 2026-09-03
**Status**: Draft
**Input**: Reproduction from `/spec-kitty.tasks` for Mission `planning-artifact-ancestry-fix-01M1K666` and explicit user authorization for a separate resolver repair.

## Intent Summary

When an operator runs a planning prerequisite command from a validated linked task worktree and supplies an exact Mission slug or immutable Mission ID, Spec Kitty must resolve that Mission from the owned checkout instead of discarding the selector and falling back to the primary checkout's global Mission census. Explicit selectors remain fail-closed when missing or ambiguous, and planning commands must not write Mission artifacts into the primary checkout.

## User Scenarios & Testing

### User Story 1 - Continue planning from an owned task worktree (Priority: P1)

As a Spec Kitty operator, I want an explicit Mission selector to resolve inside the linked task worktree I am using so that `check-prerequisites` can hand a trustworthy absolute feature directory to the tasks workflow.

**Why this priority**: The current defect blocks task generation even though canonical action context already resolves the same selector correctly.

**Independent Test**: Create a Mission only in a clean linked task worktree, then run `check-prerequisites` with its exact slug and immutable ID from that worktree.

**Acceptance Scenarios**:

1. **Given** a validated linked task worktree containing a Mission absent from the primary checkout, **When** the operator supplies the exact slug, **Then** prerequisites succeed and report the absolute Mission directory in that worktree.
2. **Given** the same Mission, **When** the operator supplies its immutable Mission ID, **Then** the same directory and branch contract are returned.
3. **Given** a successful resolution, **When** the primary checkout is inspected, **Then** no Mission planning artifact has been created or modified there.

### User Story 2 - Preserve fail-closed selector behavior (Priority: P1)

As a Spec Kitty operator, I want invalid or genuinely ambiguous selectors to remain refused so that the repair cannot silently choose a plausible but incorrect Mission.

**Why this priority**: Selector integrity is load-bearing for ownership, branch routing, and task finalization.

**Independent Test**: Run equivalent commands with a missing selector and with deliberately ambiguous candidates, and confirm that neither produces a usable feature directory.

**Acceptance Scenarios**:

1. **Given** no Mission matching an explicit selector, **When** prerequisites run, **Then** they return a structured not-found failure rather than selecting another Mission.
2. **Given** an ambiguous selector, **When** prerequisites run, **Then** they return the canonical ambiguity failure and list no successful target.
3. **Given** no selector in a multi-Mission repository, **When** prerequisites run, **Then** the existing explicit-selection requirement remains enforced.

### User Story 3 - Keep planning command surfaces consistent (Priority: P2)

As an operator, I want context resolution and prerequisite resolution to agree on the Mission and branch so that generated follow-up commands are executable without manual path fallback.

**Why this priority**: A resolver that succeeds only in one command still leaves the workflow internally inconsistent.

**Independent Test**: Resolve action context and then execute its returned prerequisite command for the same linked-worktree Mission; both must report the same Mission identity and task branch.

**Acceptance Scenarios**:

1. **Given** an exact Mission selector, **When** action context emits a prerequisite command, **Then** executing that command succeeds for the same Mission.
2. **Given** a resolved task branch, **When** prerequisite output is inspected, **Then** current and target branch values match the owned task-worktree contract.

### Edge Cases

- The same human-readable slug exists on more than one discoverable surface with different immutable identities.
- A registered linked worktree exists but its Mission directory or metadata is incomplete.
- The supplied handle is a full slug, an immutable Mission ID, or its supported short identity prefix.
- The primary checkout contains hundreds of unrelated Missions.
- The command is invoked from the primary checkout rather than a linked task worktree; current primary behavior must remain compatible.

## Domain Language

- **Owned checkout**: The validated repository checkout explicitly or canonically associated with the current planning invocation.
- **Linked task worktree**: A registered Git worktree on a task-owned branch, distinct from the primary checkout.
- **Explicit Mission selector**: A supplied full slug, immutable Mission ID, or supported short identity prefix.
- Avoid **main repository** when referring to filesystem placement; use **primary checkout** or **linked task worktree**.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Resolve explicit slug in owned worktree | As an operator, I can run prerequisites with an exact slug for a Mission present only in my validated linked task worktree. | High | Open |
| FR-002 | Resolve immutable identity equivalently | As an operator, I receive the same Mission directory when selecting the Mission by immutable ID or another supported exact identity form. | High | Open |
| FR-003 | Preserve structured refusal | As an operator, I receive a structured refusal for missing, ambiguous, or omitted selectors instead of a silently selected Mission. | High | Open |
| FR-004 | Keep resolver command parity | As an operator, the prerequisite command emitted by action-context resolution succeeds for the same Mission and branch contract. | High | Open |
| FR-005 | Protect primary placement | As an operator, resolving or validating a linked-worktree Mission creates or changes zero planning artifacts in the primary checkout. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Cross-platform regression evidence | The focused suite passes on Windows and a POSIX CI runner with zero new platform-specific skips. | Portability | High | Open |
| NFR-002 | Deterministic parity | Repeating the same explicit-selector scenario through context and prerequisites produces one identical Mission directory and branch verdict in 100% of focused runs. | Reliability | High | Open |
| NFR-003 | No primary side effects | Each linked-worktree prerequisite reproduction produces zero primary-checkout file changes and zero primary-branch commits. | Safety | High | Open |
| NFR-004 | Focused quality gate | All focused selector, prerequisite, read-path, and planning-surface tests pass before review, with no retry-to-green. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical selector authority | The repair must reuse the existing canonical Mission selector/read-path authority rather than add a command-local directory scan. | Architecture | High | Open |
| C-002 | No ambiguity bypass | The repair must not convert ambiguous, missing, or omitted selectors into a successful fallback. | Safety | High | Open |
| C-003 | No primary-authoring fallback | The repair must not copy or author task-worktree planning artifacts into the primary checkout. | Safety | High | Open |
| C-004 | Existing runtime only | The Mission does not install, publish, release, deploy, or replace the active Spec Kitty CLI. | Delivery | High | Open |
| C-005 | PR-only delivery | Durable changes land through the task branch and a pull request to fork `main`; no direct protected-branch write is allowed. | Delivery | High | Open |

## Assumptions

- Git worktree registration and the task branch are valid before the resolver runs.
- The existing action-context resolver result for the reproduction is correct and can serve as parity evidence.
- Windows origin binding's missing `fcntl` module is separately tracked and is not part of this Mission.
- The old upstream PR `#3429` is closed without merge and is evidence only; its 971-commit-stale branch will not be reused.
- This is a focused resolver bug fix, not a bulk rename or a redesign of every planning artifact placement rule.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Both exact slug and immutable Mission ID make the previously blocked prerequisite command succeed from a clean linked task worktree on the first run.
- **SC-002**: Context resolution and its emitted prerequisite command report the same Mission directory and task branch in every focused acceptance case.
- **SC-003**: Missing, ambiguous, and omitted selector controls retain 100% of their existing refusal scenarios.
- **SC-004**: The primary checkout remains byte-clean and commit-clean across every linked-worktree acceptance reproduction.
- **SC-005**: The original ancestry Mission can resume `/spec-kitty.tasks` without a manual file-placement fallback after the repaired branch is integrated and made available through the separately governed delivery path.
