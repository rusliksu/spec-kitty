# Implementation Plan: Task and status commands honour an owned checkout

Mission: `tasks-status-owned-checkout-seam-01M282V3` | Bead: `spk-8o2` | Issue: #26 | Type: software-dev | Topology: single_branch

## Summary

Add the missing `--owned-checkout` seam to the command families that record work-package state, by
reusing the pattern that already works for `next`: validate the declared path through
`resolve_ownership_claim`, refuse fail-closed through the shared typed error, and use the claimed
checkout as the repo root for mission resolution, status placement and the transaction identity. The
no-opt-in path stays byte-for-byte as it is.

## Branch Contract

- Work surface: `codex/tasks-status-owned-checkout` in the owned worktree
  `C:\Users\Ruslan\.codex-worktrees\spec-kitty-tasks-status-owned-checkout`.
- Planning artifacts land on the same branch (single_branch topology via
  `spec-kitty spec-commit --owned-checkout`; this very mission exercises the seam it is adding).
- Merge target: `main`. The protected primary checkout is never modified (C-003).

## Technical Context

- Python 3.11+; CLI built with Typer in `src/specify_cli/cli/commands`.
- Reused authorities: `core/checkout_ownership.py` (claim validation), `core/paths.py`
  (`locate_project_root`), `cli/selector_resolution.py` (`resolve_mission_handle`),
  `cli/commands/next_cmd.py` (the sanctioned option pattern),
  `coordination/status_transition.py` (the canonical status writer).
- Test entry points: `tests/cli/commands/`, `tests/tasks/`, `tests/status/`, plus the
  architectural gates for the touched packages.
- Windows note: the sync shard is not touched by this mission, so no import shim is needed.

## Constitution Check

- **024 locality / 025 boy-scout**: the change is an option plus a root-selection branch in two command
  families and their shared helpers; the ownership authority is reused, not extended.
- **030 test-and-typecheck gate / 034 test-first**: the acceptance test that reproduces issue 26 lands
  before the production change; ruff and mypy run on the changed files.
- **043 close the defect class by construction**: one seam, applied to every state-recording command,
  instead of per-command workarounds.
- **044 canonical sources**: the ownership claim is the single validation authority; the canonical
  status event log stays the single writer (C-002).
- **033 targeted staging / 045 PRs-only**: mission files only, one task branch, delivery by PR.
- **C-004**: the in-flight PR 20 approach is recorded in `research.md` (D-6) rather than resolved by
  conflict resolution.

No exception requested.

## Architecture

```
command (move-task | status emit/validate/...)
   |
   |-- no --owned-checkout ----------------------> existing guarded path (unchanged)
   |
   '-- --owned-checkout <path>
          resolve_ownership_claim(path, resolved_primary=locate_project_root())
             |-- not OWNED -> error_for_claim -> typed refusal, exit 1, writes nothing
             '-- OWNED -> repo_root = claim.claimed_checkout
                            |
                            |-- mission census = <claimed>/kitty-specs  (resolve_mission_handle)
                            |-- status state placement via placement_seam(claimed, slug, STATUS_STATE)
                            '-- transaction identity from claimed root + feature dir + mission anchor
```

## Project Structure

### Documentation (this mission)
- `kitty-specs/tasks-status-owned-checkout-seam-01M282V3/spec.md`, `research.md`, `data-model.md`,
  `plan.md`, `tasks.md`, `wps.yaml`, `tasks/WP*.md`, `traces/`.

### Source Code
- `src/specify_cli/cli/commands/agent/tasks_move_task.py` and its shared helpers — lane transitions.
- `src/specify_cli/cli/commands/agent/status.py` — canonical status commands.
- Tests under `tests/tasks/` and `tests/status/` (new owned-checkout acceptance suite plus additions
  to existing suites).

## Implementation Concern Map

### IC-01 — The seam itself (FR-001, FR-003, FR-005)

An option on the command, the guard bypass copied from `next_cmd` (only the syntactic
`.worktrees` guard), claim validation through the shared authority, typed refusal through
`_emit_checkout_ownership_error`-equivalent, and `repo_root = claim.claimed_checkout`. Prove the
no-opt-in path is unchanged.

### IC-02 — Lane transitions and review verdicts (FR-002, FR-004)

`move-task` and `status emit` (with review-result payloads) must resolve the mission in the claimed
checkout and write the canonical event there. The acceptance test drives the full issue-26 sequence
against a real owned worktree and asserts the primary checkout is untouched (NFR-004).

### IC-03 — Planning-side commands (FR-006)

`tasks` / `finalize-tasks` / `research` either honour the same seam or refuse with an actionable
message; a silent write into the protected primary is the failure mode being removed.

### IC-04 — Evidence (NFR-001, NFR-003)

The issue-26 reproduction recorded end to end, the local suites, and the POSIX CI verdicts at one
candidate SHA, with no new skip.

## Verification Strategy

1. RED: the acceptance test drives `move-task` from a real owned worktree with the checkout declared
   and fails on the current head with `mission_not_found`.
2. GREEN: after the seam, the transition is recorded in the owned mission's canonical status log.
3. Negative controls: undeclared path still refuses; a directory that is not a worktree of the primary
   refuses; the primary checkout proves unchanged.
4. Static: ruff, mypy on changed modules, `git diff --check`.
5. Cloud: POSIX CI green at the candidate SHA for the affected suites and the architectural gates.

## Complexity Tracking

No exception requested: one new option per command family, no new module, no new writer, no schema
change.

## Parallel Work Analysis

### Dependency Graph
```
IC-01 (seam) -> IC-02 (transitions + verdicts) -> IC-03 (planning-side) -> IC-04 (evidence)
```

### Work Distribution
Two work packages: WP01 covers IC-01 + IC-02 (seam plus the two state-recording surfaces, with the
acceptance test that proves issue 26 is closed), WP02 covers IC-03 + IC-04 (planning-side
honour-or-refuse and the both-platform evidence).

### Coordination Points
- The candidate SHA for the CI evidence must be the one the local evidence names.
- PR 20 may land concurrently; if it does, its `tasks_move_context.py` and this seam must be
  reconciled in favour of one authority, recorded in the review trail.
