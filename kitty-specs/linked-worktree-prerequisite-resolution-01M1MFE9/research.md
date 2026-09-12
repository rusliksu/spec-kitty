# Research: Linked Worktree Prerequisite Resolution

## Finding 1: The working command already demonstrates the intended seam

**Decision**: Treat `agent context resolve` as the reference architecture because it calls `resolve_mission_operation_context()` and successfully resolves the linked-worktree-only Mission.

**Rationale**: This is current repository code with live reproduction evidence, not a speculative replacement.

**Alternative rejected**: Add another filesystem walk to each failing command. That would duplicate identity rules and weaken conflict handling.

## Finding 2: Repository root and Mission anchor are different authorities

**Decision**: Retain primary `repository_root` for Git topology and protection policy while using `mission_anchor_root` for Mission artifacts.

**Rationale**: Replacing the repository root wholesale would break topology assumptions; ignoring the caller anchor causes the present failure.

**Alternative rejected**: Pass the linked worktree as if it were the primary repository root everywhere.

## Finding 3: Failure is a consumer-adoption gap

**Decision**: Migrate `check-prerequisites`, `setup-plan`, decision open/verify, and spec-commit to the existing operation context before changing lower-level read-path semantics.

**Rationale**: `operation_context.py` already models caller-vs-primary identity, prefers a valid caller-owned hit, and refuses conflicting identities. Current failing consumers still call primary-anchored helpers directly.

**Alternative rejected**: Rewrite `resolve_handle_to_read_path()` globally. Its topology-aware primary/coord behavior serves many callers and would widen risk beyond the reproduced planning surfaces.

## Finding 4: Old PR #3429 is evidence, not a base

**Decision**: Do not revive or cherry-pick the closed unmerged branch directly.

**Rationale**: It is 971 commits behind current fork `main`; current code already contains a newer operation-context implementation. Only its historical intent is relevant.

## Finding 5: Bootstrap failures are part of acceptance evidence

**Decision**: Pin the exact current failures for prerequisites, setup-plan, decision open/verify, and spec-commit, then verify all through the same caller-owned Mission fixture.

**Rationale**: Fixing only the first visible command would leave the next workflow step blocked and would not meet the user-confirmed shared scope.
