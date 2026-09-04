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

## 2026-09-04 — approved C1/U1 planning correction

Ruslan approved correcting both analysis findings without weakening the charter.
Preserve three sequential WPs and all historical product RED commits. WP01 now
owns a reusable harness and its own RED-to-GREEN acceptance, in two explicitly
declared create-intent files. WP02 owns read-consumer success acceptance; WP03 owns
write-consumer acceptance and the existing complete mixed contract. No product
assertion may be deleted, inverted, skipped or xfailed to obtain approval. The
final Mission gate still runs the whole focused inventory, not WP-specific filters.

NFR-004 now names the per-WP and final-Mission gates explicitly. NFR-001 remains
unchanged and is operationalized in T012/DoD: same candidate SHA, Windows plus
POSIX CI, exact test inventory/commands and result/skip counts, zero new
platform-specific skips. Existing ci-quality jobs are discovery entrypoints, not
assumed execution evidence. Unavailable CI is pending, not waived.

This is planning only: no test/source implementation, no WP approval, no CI
dispatch, push or install. The prior analysis report is retained as historical
evidence and becomes stale after these input changes. Re-analysis is required.
The finalizer's initial missing-file ownership refusal was resolved by declaring
create_intent, not by prematurely creating implementation files; the repeated
validate-only check passed with 3 WPs, 3 lanes and no ownership warnings.
