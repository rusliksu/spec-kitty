# Research: Owned-checkout seam for the task and status commands

Mission: `tasks-status-owned-checkout-seam-01M282V3` | Bead: `spk-8o2` | Issue: #26
Date: 2026-09-11

## Question

Why can `next`, `spec-commit` and `agent mission create` address a mission that lives in an owned
linked worktree while every command that records work-package state cannot, and what is the smallest
change that closes that gap without touching non-owned routing?

## Evidence base

**D-1 - the working pattern already exists.** `src/specify_cli/cli/commands/next_cmd.py` declares
`--owned-checkout`, wraps the command with `_require_main_repo_unless_owned` (which bypasses only the
syntactic `.worktrees` guard when the option is present), and in the body resolves the claim through
`resolve_ownership_claim(owned_checkout, resolved_primary=ambient_root)`; a refusal is rendered by
`_emit_checkout_ownership_error` and the command exits fail-closed. On success it uses
`claim.claimed_checkout` as the repo root and as the effective root. The same pattern is used by
`agent mission create` and `spec-commit`.

**D-2 - the ownership authority is shared and typed.** `src/specify_cli/core/checkout_ownership.py`
owns `OwnershipClaim`, `OwnershipValidationResult` (`OWNED`, `UNOWNED_NO_OPT_IN`, `NESTED`,
`FOREIGN_OR_MISMATCHED`, `BROKEN_POINTER`) and the typed error family, with `resolve_ownership_claim`
and `error_for_claim`. This is exactly the validation FR-003 asks for; no new validation may be
written.

**D-3 - the failing commands resolve their census from the ambient root.** `tasks_move_task.py` calls
`_tasks.locate_project_root()` and `tasks_shared.py` resolves the mission against that root;
`selector_resolution.resolve_mission_handle` hands the handle to `resolve_mission(handle, repo_root)`,
and `locate_project_root` is documented to return the **main** repository root from inside a worktree.
The owned mission therefore never appears in the census, and every selector form (slug, mid8, ULID)
returns `mission_not_found`.

**D-4 - `SPECIFY_REPO_ROOT` is not a workaround.** Setting it to the owned worktree still returns
`mission_not_found` because the resolver routes the value through `get_main_repo_root`, which collapses
a linked worktree back to the primary.

**D-5 - the write side is already parameterised by the root.** `coordination/status_transition.py`
derives its transaction identity from the `repo_root`, `feature_dir` and mission anchor carried on the
request, and `tasks_shared.py` places the status state through `placement_seam(main_repo_root,
mission_slug, kind=STATUS_STATE)`. Feeding the claimed checkout as that root is therefore a routing
decision, not a new writer (C-002).

**D-6 - an independent fix exists in flight.** Pull request 20 (mission
`linked-worktree-prerequisite-resolution-01M1MFE9`) carries `tasks_move_context.py` and
`test_move_task_owned_checkout.py` for `move-task`. A cherry-pick onto current `main` conflicts in
`status_transition._identity_for_request`, where that branch restructures the destination-ref
resolution. This mission must not resolve that conflict blindly (C-004); it implements the seam
through the shared ownership authority instead, and records the difference.

**D-7 - the previous mission's friction.** During
`sync-capture-coalescing-integrity-01M25WZF` the same gap stopped the runtime at `implement` with
`no actionable wp`, and `spec-kitty research` (no seam at all) wrote four scaffold files into the
protected primary checkout. Both are recorded in that mission's `traces/tooling-friction.md` on
`main`.

## Decisions

**RD-001 - reuse the ownership authority, add no new validation.** The new option resolves through
`resolve_ownership_claim` and refuses through `error_for_claim`, exactly like `next`.

**RD-002 - explicit declaration only.** No environment variable, cwd heuristic or ambient detection may
enable the seam (NFR-002). `SPECIFY_REPO_ROOT` gains no new meaning.

**RD-003 - the declared checkout becomes the repo root for the command.** Mission resolution, status
state placement and the transaction identity all read from the claimed checkout; nothing else about
routing changes.

**RD-004 - no-opt-in behaviour is byte-for-byte identical.** The opt-in branch is additive; the guarded
path stays as it is (C-001, FR-005).

**RD-005 - planning-side commands either honour the seam or refuse loudly.** Writing into the protected
primary for a mission that lives elsewhere is never an acceptable outcome (FR-006).

## Impact analysis

- `src/specify_cli/cli/commands/agent/tasks_move_task.py` and the shared task helpers: option
  plumbing plus claimed-root resolution.
- `src/specify_cli/cli/commands/agent/status.py`: the same option for `emit`, `validate`,
  `materialize` and `lifecycle`.
- Tests: a new owned-checkout acceptance suite plus additions to the existing move-task and status
  command suites.
- Unchanged: the ownership authority, the canonical status event log, the mission manifest, the sync
  layer, and every non-owned route.

## Open questions and risks

- **R-1**: whether the canonical status writer needs an explicit owned-mission route for
  `single_branch` topology or whether feeding the claimed root is sufficient. Resolved by the WP01
  acceptance test; if a route is needed it must reuse the existing writer (C-002).
- **R-2**: `tasks.md` checkbox updates and the WP frontmatter bootstrap must land in the owned
  checkout, not the primary.
- **R-3**: PR 20 may land first; the two approaches overlap in `move-task`. The mitigation is to keep
  this mission's change additive and to record the difference in the review trail.

## Sources

`research/source-register.csv`, `research/evidence-log.csv`.
