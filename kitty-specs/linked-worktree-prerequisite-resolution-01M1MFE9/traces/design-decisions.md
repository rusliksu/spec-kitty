# Design Decision Trace

## DD-001 — Shared operation context

Use `resolve_mission_operation_context()` as the single authority for choosing repository and Mission roots.

## DD-002 — Preserve split authorities

Git topology/protection remains anchored to `repository_root`; Mission artifacts use `mission_anchor_root`.

## DD-003 — Consumer migration before resolver rewrite

Move the four reproduced command families onto the existing seam. Change the seam itself only if RED tests reveal a missing invariant.

## DD-004 — Fail closed

Preserve typed ambiguity, missing-selector, unsafe-token, and conflicting-identity failures. Never fall back to a global Mission census after an exact caller-owned hit.

## DD-005 — Sequential lane

The affected consumers share identity fixtures and authority rules, so work remains sequential rather than split into parallel writers.

## DD-006 — Carry lifecycle projections into WP reads

The approved recovery passes the existing validated `effective_root` to WP
metadata and lane-manifest reads through `read_dir_for`. It carries the existing
`status_surface.status_read_dir` into WP lookup rather than re-deriving status
from the repository root. An explicit anchor without its status projection is
refused. Default callers retain their previous placement-seam behavior.

Workspace registries, allocation paths and checkout-identity enforcement continue
to use `repo_root`. Metadata caches include the selected checkout to prevent
cross-checkout reuse. This is a read-context repair, not authorization to allocate
a lane, transition a WP, or approve its implementation. Workflow/task command
selection and the actual implement/review transitions remain a subsequent slice.

## 2026-09-04 — retain artifact context through analysis persistence

Use the existing Mission-level `mission_context_for` projection for a validated
caller-owned Mission; it already supplies the analysis report's read directory,
write directory and commit target. This avoids extending PlacementSeam or creating
a recorder-specific path resolver. Legacy primary/coord callers keep their current
seam. Hash relativization and the implement freshness check use the selected
artifact root; charter resolution independently retains its canonical authority.
The dirty preflight must inspect that same selected checkout because
`locate_project_root()` intentionally returns the repository-root checkout.
