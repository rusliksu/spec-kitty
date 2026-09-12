# Data Model: Owned-checkout seam for the task and status commands

Mission: `tasks-status-owned-checkout-seam-01M282V3`

## Entities

**Owned checkout declaration** (new CLI input, not persisted)
- an absolute path supplied by the caller on the command line;
- validated by `resolve_ownership_claim(path, resolved_primary=locate_project_root())`;
- carries an `OwnershipValidationResult`; only `OWNED` proceeds.

**Ownership claim** (existing, `core/checkout_ownership.py`)
- `claimed_checkout`, `validation_result`, and the typed refusal family
  (`UnownedNoOptInError`, `NestedCheckoutError`, `ForeignOrMismatchedCheckoutError`,
  `BrokenPointerCheckoutError`).

**Mission census** (existing)
- the missions discoverable under a checkout's `kitty-specs/`; becomes the **claimed** checkout's
  census when the seam is used.

**Lane transition** (existing canonical status event)
- written through `coordination/status_transition.py`; its transaction identity is derived from the
  request's repo root, feature dir and mission anchor.

**Review result** (existing)
- the structured verdict attached to a transition out of review; unchanged shape.

## Relationships

```
declared checkout --resolve_ownership_claim--> OwnershipClaim(OWNED)
      |
      +--> repo root for mission resolution (census = <claimed>/kitty-specs)
      +--> status state placement (placement_seam(claimed, mission_slug, STATUS_STATE))
      +--> transaction identity (repo_root / feature_dir / mission anchor)
      '-x- never --> the protected primary checkout
```

## Invariants

- **I-1**: without the declaration, every route is byte-for-byte the pre-change route.
- **I-2**: a declaration that is not `OWNED` writes nothing and exits fail-closed with the typed error.
- **I-3**: with an `OWNED` declaration, no write reaches the primary checkout (proved by HEAD,
  cleanliness and file-set comparison).
- **I-4**: the canonical status event log remains the only authority for lane state.
- **I-5**: the mission census used for resolution and the root used for writes are the same checkout.
