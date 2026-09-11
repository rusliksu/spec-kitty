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

## Addendum: the first implementation pass and the folds that remain

A first pass on `move-task` (option + validated claim + claimed root as the command's root, plus
skipping the primary fold in `_ensure_target_branch_checked_out`) moved the failure from
`mission_not_found` to a deeper refusal, which is itself the useful finding: **the resolution stack
folds a linked worktree back to the primary in more than one place**, and the command therefore needs
the owned root threaded further than the option surface.

Observed with the partial pass, run from this mission's own worktree:

```text
without --owned-checkout   -> {"error": "mission_not_found", "handle": "<slug>"}   (unchanged, parity held)
with    --owned-checkout   -> {"error": "meta.json not found for mission '<slug>' at
                               C:\\Users\\Ruslan\\spec-kitty\\kitty-specs\\<slug>"}
```

**D-8 - the remaining fold sites (all read the primary, none sees an owned root):**

- `src/mission_runtime/resolution.py:1027` (`primary_root = get_main_repo_root(repo_root)` in the
  topology-only resolver) and `:1083` in `mission_context_for`. The latter already accepts an
  **`effective_root`** and documents that folding an owned checkout through `get_main_repo_root`
  'would silently cross-read a sibling checkout (#3328 / C-002)' — this is the sanctioned seam and
  the one the remaining work must thread.
- `src/mission_runtime/lifecycle_phase.py:107, 264, 383` — the same fold in the lifecycle phase
  helpers.
- `src/specify_cli/missions/_read_path_resolver.py:1308` — `primary_dir = get_main_repo_root(repo_root)
  / KITTY_SPECS_DIR / mission_slug`.
- `src/specify_cli/coordination/surface_resolver.py:764` — `_compose_primary_feature_dir(repo_root, ...)`
  composed the primary path the final refusal named; this is the status-surface side of RD-003 and the
  reason R-1 is answered 'a route IS needed'.
- `src/specify_cli/cli/commands/agent/tasks_shared.py` `_find_mission_slug` legacy-dir probe
  (folds for an existence check only; harmless but part of the same family).

**Consequence for the plan**: WP01 is not an option-plumbing change. The seam must thread the
declared checkout as the **effective root** through `mission_context_for` and the surface resolver,
which is the same layer the in-flight PR 20 touches from the other direction (C-004). The working
method stays: keep the no-declaration path byte-identical (proved above), thread the effective root
through the sanctioned seam, and let the acceptance test decide when the seam is complete.

**D-9 - the concrete call chain that must carry the effective root.** Traced on this revision:

```text
move-task (tasks.py)
  -> _do_move_task -> _mt_resolve_targets (tasks_move_task.py)
       repo_root            = resolve_repo_root_with_owned_checkout(...)   # claimed checkout when declared
       main_repo_root       = _ensure_target_branch_checked_out(..., owned_root=repo_root)
  -> _mt_build_request   -> TransitionRequest(repo_root=..., ...)
  -> coordination/status_transition.py
       _identity_for_request  -> resolve_status_surface_with_anchor(repo_root, mission_slug)   # line 622
       _primary_anchor()      -> placement_seam(...).read_dir(PRIMARY_METADATA)
  -> coordination/surface_resolver.py
       resolve_status_surface_with_anchor -> _compose_primary_feature_dir(repo_root, slug)      # line 764
                                            |
                                            '-> folds the linked worktree back to the primary
```

The two functions that need an explicit **`effective_root`** parameter are therefore
`resolve_status_surface_with_anchor` and its thin wrapper `resolve_status_surface` (both currently
take only `repo_root`, `mission_slug`, `topology`), and the transition request must be able to carry
the declared checkout so `status_transition` and `_primary_anchor` stop folding. `mission_context_for`
already accepts `effective_root` (line 1083) and is the model for the parameter shape; the same
treatment is needed in `lifecycle_phase.py` (lines 107, 264, 383) and
`missions/_read_path_resolver.py:1308`.

This is the bounded implementation left for WP01: an additive `effective_root` parameter on the
surface resolver pair, carried on the transition request from the task command, with the
no-declaration path proved byte-identical.

**D-10 - the layer already owns the seam; its factory just does not expose it.** `mission_runtime
/resolution.py` threads an `effective_root` through `mission_context_for` (line 1085),
`resolve_action_context` (line 2224), the meta-path composer (line 225) and the fragment assemblers —
the whole layer is already built for an explicitly declared root. The fold survives because the
*factory* `placement_seam(repo_root, mission_slug)` (line 2198) and `PlacementSeam` itself do not
accept or carry it, so every caller that builds a seam from a bare root re-folds to the primary.

The remaining WP01 change is therefore, in the layer's own idiom:

1. `placement_seam(repo_root, mission_slug, *, effective_root=None)` forwarding into
   `PlacementSeam`, and `PlacementSeam` using it wherever it resolves an artifact home;
2. `resolve_status_surface` / `resolve_status_surface_with_anchor` gaining the same optional
   parameter and using `effective_root or repo_root` for `candidate_feature_dir_for_mission` and
   `_compose_primary_feature_dir`;
3. `TransitionRequest.effective_root` (status/models.py already defaults every field, so the
   addition is compatible) carried from the task command, used by
   `status_transition._canonical_primary_feature_dir` (line 564) for both its seam call and its
   resolver call;
4. the same treatment for `lifecycle_phase.py` and `missions/_read_path_resolver.py:1308` where
   they compose the primary dir from a bare root.

The no-declaration path stays byte-identical throughout, which the parity check in D-8 already
demonstrates for the option surface.

**D-11 - the fold bottoms out in one guarded leaf.** After threading `effective_root` through the
placement seam factory, `resolve_artifact_surface`, `resolve_placement_only`, both status-surface
resolver functions, `TransitionRequest` and `locate_work_package`, the owned run still ends in the
same refusal. A stack probe on the live CLI located the last fold:

```text
_mt_resolve_targets -> task_utils/support.locate_work_package -> surface_resolver.resolve_status_surface
  -> mission_runtime/_read_path_resolver._compose_primary_feature_dir   (line 1263)
       primary_dir = get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug   (line 1308)
```

`_compose_primary_feature_dir` is the terminal KITTY_SPECS join, and it folds **every** root it is
handed through `get_main_repo_root`; every layer above inherits that fold. The leaf documents itself
as permanent (C-004, never delete) and is machine-guarded: its sanctioned-import census lives in
`tests/architectural/test_no_read_side_bypass.py` (`_FOUNDATION_SANCTION_SEED` +
`_READ_SANCTIONED_MODULES`) and `tests/architectural/test_single_mission_surface_resolver.py` owns
the join. Closing issue 26 therefore has exactly two coherent shapes:

1. give that leaf an explicit owned-root parameter and update the two architectural censuses that
   sanction its callers (the seam this mission has already threaded is the correct upstream); or
2. adopt the placement-layer approach of the in-flight pull request 20, which changes
   `_read_path_resolver` and the task-context routing from the other direction (C-004).

Everything threaded so far is additive and verified non-regressive: `tests/mission_runtime/`, the
move-task orchestration suite and the compat-surface guard are **653 passed, 0 failed**, and the
no-declaration path still returns `mission_not_found` for an owned mission (parity held).

**Scope note**: the seam legitimately spans shared helpers outside the command files named in
`wps.yaml` — `task_utils/support.py` (the work-package locator), `mission_runtime/resolution.py`,
`coordination/surface_resolver.py` and `status/models.py`. WP01's `owned_files` must be widened to
name them, or the change is split across WPs; that is a plan edit, not a silent expansion.

## Sources

`research/source-register.csv`, `research/evidence-log.csv`.
