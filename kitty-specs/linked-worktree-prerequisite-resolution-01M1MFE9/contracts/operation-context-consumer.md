# Contract: Planning Command Operation Context

| Situation | Selected Mission surface | Result |
|---|---|---|
| Exact selector exists only in validated caller worktree | Caller `mission_anchor_root` | Success |
| Exact selector exists only in primary checkout | Primary `mission_anchor_root` | Existing success behavior |
| Same immutable identity exists on both surfaces | Caller surface for caller-owned planning operation | Success |
| Selector resolves to different identities on both surfaces | None | Typed conflict refusal |
| Selector is missing | None | Typed not-found refusal |
| Selector is ambiguous | None | Canonical ambiguity refusal |
| Selector is omitted in a multi-Mission repository | None | Explicit-selection refusal |
| Selector is unsafe/path-like | None | Traversal/input refusal before path access |

## Consumer Obligations

- `check-prerequisites` reports the selected absolute Mission directory and owned branch contract.
- `setup-plan` reads and writes plan artifacts only at the selected Mission surface.
- decision open/verify records and inspects decisions only for the selected immutable Mission.
- `spec-commit` validates file ownership against the selected surface and keeps existing protection/commit routing.
- Every consumer exposes structured failures; none retries by scanning all Missions or silently switches to primary.
