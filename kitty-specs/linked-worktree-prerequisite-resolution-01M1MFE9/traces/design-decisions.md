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

## 2026-09-05 — Owned planning allocation boundary

Ruslan requested continuation of the safe owned-planning-checkout allocation
package. Read-only tracing shows this is a multi-consumer recovery, not removal
of the first refusal. No allocation code or lifecycle state changed in this pass.

Verified consumers on `274671e82`:

- `workflow_executor.ensure_workspace_materialized` refuses every worktree cwd.
- The internal `implement` command independently has `@require_main_repo`.
- `_detect_wp_context`, status/lanes reads and workspace resolution inside that
  command still derive Mission artifacts from its single repository-root input.
- `create_lane_workspace` invokes the existing allocator, records base provenance
  in the supplied WP file and saves WorkspaceContext in the repository registry.
- Allocator topology discovery, reuse self-heal and claim ancestry independently
  read Mission metadata/manifests. They must consume the same validated anchor;
  repairing only fresh creation would leave resume or claim inconsistent.

### Boundary decision

Retain DD-006: canonical repository root owns Git topology, lane placement and
the existing `.kittify/workspaces/<workspace-name>.json` registry. The validated
Mission anchor owns planning artifacts and the canonical status projection.
Do not introduce a second registry or copy planning artifacts into primary.

NFR-003 explicitly applies to prerequisite reproductions; it is not a blanket
ban on allocation's Git/context bookkeeping. Allocation evidence must enumerate
these expected operational writes separately, preserve primary tracked files,
primary branch HEAD and primary index, and prove zero primary Mission-artifact
writes. This distinction does not waive prerequisite byte-clean checks.

### Implementation package and verification

1. Resolve caller ownership through the existing MissionOperationContext and
   branch/checkout-identity authorities. A matching slug alone is insufficient:
   require registered same-repository ownership, exact immutable identity and
   the declared planning branch. Reject foreign/unregistered/dirty/conflicting
   callers before allocation; keep the ordinary primary path compatible.
2. Carry that operation context through materialization and the internal command,
   retaining separate repository and artifact roots. Do not globally weaken
   `require_main_repo`, fake cwd, pass the artifact root as Git topology root, or
   call an undecorated implementation to bypass the existing guard.
3. Thread the same anchor through allocator topology reads, reuse self-heal,
   claim preconditions and status/commit placement. Keep husk, protected-branch,
   dependency, recorded-planning-SHA and ancestry checks in force. Record actual
   base provenance; use the existing allocator and status transaction authority.
4. Before implementation, commit real-Git acceptance RED for slug and immutable
   ID through the public `agent action implement` entrypoint. A successful run
   must create exactly the predicted registered lane containing the planning
   commit and emit the expected canonical claim state only after preconditions.
   Assert primary HEAD/index/tracked bytes and primary Mission absence unchanged;
   enumerate operational registry writes rather than hiding them in a snapshot.
5. Cover repeat invocation/reuse, dirty caller/lane, foreign checkout, identity
   conflict, missing/corrupt manifest, husk and unresolved dependencies. Refusals
   must not create a lane or emit a claim; do not demand zero Git metadata churn
   from successful creation. Verify significant identity/path mutations fail.
6. Run focused allocation, single-resolution, claim, ancestry, placement and
   checkout-identity suites, Ruff and strict mypy. Only then repeat the actual
   WP01 command and inspect exact registered path, branch, state and write set.

Scope remains allocation recovery for the existing Mission/Bead, not WP01 harness
completion, WP02, review approval, push, runtime installation or deployment.
The prior ready analysis describes the existing core planning inputs; it is not
implementation evidence for this recovery. If implementation requires changing
the ownership boundary above, stop for a material scope decision.
