# Data Model: Mission Operation Context Adoption

No persisted model or schema changes are required.

## MissionOperationContext

Existing immutable runtime value with three authorities:

- `repository_root`: canonical primary repository used for Git topology and protection.
- `mission_anchor_root`: selected checkout containing the canonical Mission artifacts.
- `identity`: resolved immutable Mission identity, or absent only for canonical miss/ambiguity handling.

## Resolution Inputs

- explicit Mission selector: full slug, immutable ID, or supported short identity
- invocation current directory
- canonical repository root
- primary and caller Mission metadata
- Git worktree registration/relationship

## Invariants

1. Caller checkout is considered only when it belongs to the same primary repository.
2. A caller-owned exact hit wins over a primary miss.
3. Primary behavior remains available when the caller has no matching Mission.
4. Different immutable identities across caller and primary fail closed.
5. Unsafe, missing, omitted, and ambiguous selectors never become successful fallbacks.
6. Artifact reads/writes use `mission_anchor_root`; Git policy uses `repository_root`.
7. No command performs a private Mission-directory census after context selection.

## State Effects

Resolution itself is read-only. Existing decision and spec-commit commands may write only after successful context selection and only through their existing event/commit routers. This Mission adds no new lifecycle state or event shape.
