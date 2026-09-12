# Implementation Plan: Linked Worktree Prerequisite Resolution

**Branch**: `codex/check-prerequisites-task-worktree-resolution` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification in `kitty-specs/linked-worktree-prerequisite-resolution-01M1MFE9/spec.md`

## Summary

Adopt the existing `resolve_mission_operation_context()` boundary across the planning command families that currently discard caller-owned linked-worktree state. Keep the canonical repository root for Git topology, use the selected `mission_anchor_root` for Mission artifact resolution, and preserve typed not-found, ambiguity, traversal, and cross-surface identity-conflict failures. Establish RED acceptance evidence first, make the smallest caller migrations, and prove that the blocked ancestry Mission's prerequisite command resolves without primary-checkout writes.

## Branch Contract

- Current/planning branch: `codex/check-prerequisites-task-worktree-resolution`
- Internal Mission target: `codex/check-prerequisites-task-worktree-resolution`
- External pull-request target: fork `main`
- Current branch matches the Mission target according to create/context output.
- No install, active-runtime replacement, release, deploy, or direct protected-branch write is in scope.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing `MissionOperationContext`, `resolve_mission_operation_context`, `ResolvedMission`, `resolve_handle_to_read_path`, planning artifact routers, Typer command surfaces
**Storage**: Existing `kitty-specs/<mission>/meta.json`, planning artifacts, and status event log; no schema or migration change
**Testing**: pytest, Typer `CliRunner`, temporary real Git repositories/worktrees
**Target Platform**: Windows, macOS, and Linux/POSIX CI
**Project Type**: Single Python CLI/runtime repository
**Performance Goals**: At most one primary/caller identity probe per planning command; no repository-wide Mission census on an exact linked-worktree hit
**Constraints**: ATDD-first separate RED commit; no command-local scans; no fail-open ambiguity; repository root and Mission anchor remain distinct
**Scale/Scope**: One existing shared context seam, four affected command families, focused unit/integration tests, and one real blocked-workflow canary

## Constitution Check

- **Canonical authority — PASS**: reuse `resolve_mission_operation_context()` rather than create another resolver.
- **ATDD-first — PASS**: linked-worktree reproductions are committed RED before caller changes.
- **Fail-closed safety — PASS**: ambiguous, missing, unsafe, and identity-conflict selectors remain typed refusals.
- **Placement integrity — PASS**: primary checkout remains Git-topology authority but never becomes a fallback authoring surface for a caller-owned Mission.
- **Cross-platform — PASS**: temporary Git worktrees and Python APIs only; no platform shell dependency in tests.
- **Campsite rule — PASS**: caller duplication is reduced by migrating to an existing seam; no broad resolver redesign is required.
- **Delivery — PASS**: task-owned branch and PR-only landing; no runtime installation or release.

## Architecture

```text
command cwd + explicit selector
          |
          v
resolve_mission_operation_context(repository_root, selector, cwd)
          |
          +-- repository_root ----> Git topology / protection / worktree registry
          |
          `-- mission_anchor_root -> Mission identity and planning artifacts
                       |
                       +-- same identity on both surfaces: caller-owned hit wins
                       +-- primary-only hit: existing primary behavior
                       +-- different identities: typed conflict refusal
                       `-- missing/ambiguous: canonical typed refusal
```

## Project Structure

```text
src/specify_cli/missions/operation_context.py
src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
src/specify_cli/cli/commands/agent/mission_setup_plan.py
src/specify_cli/cli/commands/decision.py
src/specify_cli/cli/commands/spec_commit_cmd.py

tests/specify_cli/missions/test_operation_context.py
tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py
tests/specify_cli/cli/commands/test_decision_single_authority.py
tests/specify_cli/cli/commands/test_safe_commit_cmd.py
tests/tasks/test_planning_workflow_integration.py
```

**Structure Decision**: Extend the current single-project layout. Prefer small call-site adapters that consume the existing immutable operation context. Change `operation_context.py` only if RED evidence identifies a missing invariant in the shared seam itself.

## Implementation Concern Map

### IC-01 — Verified harness and historical RED evidence

- Build a reusable real-Git fixture with a Mission present only in a registered linked task worktree.
- Drive harness correctness tests RED-to-GREEN independently of broken consumers.
- Preserve immutable product RED commits and map every success assertion to WP02
  (prerequisites/setup-plan) or WP03 (decisions/spec-commit/integrated contract).
- Assert primary checkout remains byte-clean and commit-clean.
- Preserve missing, omitted, ambiguous, traversal, and conflicting-identity failures.

### IC-02 — Read-side planning consumers

- Route `check-prerequisites` and `setup-plan` through `MissionOperationContext`.
- First commit consumer acceptance RED using WP01's verified harness; require the
  unchanged success assertions and all affected regressions GREEN before WP02 review.
- Keep repository-root preflight/protection checks anchored to the canonical primary repository.
- Resolve/read Mission artifacts through `mission_anchor_root` and canonical identity.
- Remove or bypass only the now-redundant primary-only selection inside those command paths.

### IC-03 — Decision and planning-commit consumers

- Route decision open/verify and spec-commit placement through the same operation context.
- First commit write-consumer acceptance RED, then require it and the complete
  integrated contract GREEN before WP03 review; historical RED is not final acceptance.
- Preserve write-router protection policy and ensure files must belong to the selected Mission surface.
- Refuse cross-surface identity conflicts and wrong-surface writes with actionable structured diagnostics.
- Prove the original ancestry Mission can run the exact tasks prerequisite command after integration.

**Sequencing**: IC-01 precedes IC-02 and IC-03. IC-02 and IC-03 both consume the shared seam and should be implemented sequentially in one lane to avoid overlapping resolver fixtures and authority rules.

## Verification Strategy

1. Commit focused RED tests whose failure demonstrates primary-only re-anchoring.
2. Run shared operation-context unit tests after every seam change.
3. Run each affected command family test file without filters.
4. Run planning workflow integration and architectural single-authority gates.
5. Execute the original `check-prerequisites --mission planning-artifact-ancestry-fix-01M1K666` canary from its task worktree against the built candidate.
6. Confirm both task worktrees and the primary checkout have the expected clean/dirty state; candidate execution must not alter primary.
7. Run Ruff, strict mypy on changed source, compileall, and `git diff --check`.
8. For NFR-001, record the same candidate SHA, exact commands, source/interpreter
   paths, collected/passed/failed/skipped counts and test inventory on Windows and
   POSIX CI. Require both complete focused runs GREEN with zero new platform-specific
   skips before WP03 approval and Mission acceptance. Missing CI is a pending gate.

### Reviewable test ownership (C1 correction, approved 2026-09-04)

| WP | Deliverable and acceptance scope | Final review gate |
|---|---|---|
| WP01 | `tests/tasks/linked_worktree_harness.py` and `tests/tasks/test_linked_worktree_harness.py`: registered topology, command invocation/result capture and primary snapshot invariants | Harness acceptance RED before implementation, then full harness suite plus operation-context controls GREEN; mutation of expected identity/path or a primary snapshot must fail |
| WP02 | Existing owned prerequisite/setup-plan test modules consume that harness; keep exact product-success assertions | Consumer acceptance RED before its production change, then both complete consumer suites and affected resolver guards GREEN |
| WP03 | Existing decision/safe-commit modules plus `tests/tasks/test_linked_worktree_planning_context.py` consume the harness; preserve every existing behavioral assertion | Write-consumer RED-to-GREEN, complete integrated focused inventory GREEN, and NFR-001 Windows/POSIX CI evidence |

The existing mixed contract file remains intact until WP03 reconciles it; its known
product failures are explicitly pending product work, not evidence that WP01's
harness is broken or approved. Do not delete/skip/xfail/invert those assertions.
WP01 does not edit that file or any production code. Preserve its historical RED
commits without rewriting history. Each implementation WP still needs its own
failing-first acceptance evidence for the deliverable it claims.

POSIX CI entrypoint: `.github/workflows/ci-quality.yml`,
`integration-tests-core-misc` includes `tests/tasks`; verify the actual shard,
marker selection and collected node IDs for the candidate. Related command suites
must also be covered by their CI jobs or an explicitly governed focused CI run.
A green job that omitted the focused tests is insufficient. Record run/job URLs;
Windows local evidence is allowed, POSIX CI evidence is required. This plan does
not authorize pushing a branch, changing workflow configuration, or dispatching CI.

## Complexity Tracking

### Approved lifecycle bootstrap recovery (2026-09-04)

Ruslan approved extending the recovery scope after the implement-context canary
returned WORK_PACKAGE_UNRESOLVED against the repository-root checkout. This is
an explicit bootstrap exception, not approval of WP01 or permission to start WP02.

- Recover the selected Mission context through WP lookup and workspace resolution
  in `mission_runtime/resolution.py`, `task_utils/support.py`, and
  `workspace/context.py`; restore explicit selection in `agent/workflow.py` and
  `agent/tasks_shared.py` where required for the same lifecycle path.
- Keep Git topology, lane allocation, checkout identity, dependency and review
  gates intact. Reuse MissionOperationContext and the artifact placement seam;
  do not substitute a raw path or copy Mission artifacts into the primary checkout.
- First commit real-Git RED tests for implement/review context using slug and
  immutable ID, with unchanged-primary assertions. Then repair the demonstrated
  consumers, validate emitted commands and affected compatibility/ownership tests.
- Complete WP01 evidence and obtain an independent review through the restored
  lifecycle before WP02. No manual event/status edits, push, install or deploy.
- Track this bootstrap package under Bead `spk-1m6`; no new parallel WP or lane
  is introduced while the lifecycle itself cannot resolve the Mission.

No constitution violation or new abstraction is planned. The existing operation-context seam is the intended consolidation point.

### Analysis persistence recovery (2026-09-04)

Ruslan approved the next bounded recovery package after `record-analysis` returned
`FEATURE_CONTEXT_UNRESOLVED` despite the explicit linked Mission selector. Adopt
`MissionOperationContext` and the existing `mission_context_for(..., effective_root=...)`
artifact projection in that command; retain the legacy primary/coord path for other
callers. The selected checkout must also govern dirty-tree preflight, input hash
relativization and commit placement. The implement feedback/analysis gate must hash
against that same validated root; charter hashing remains canonically anchored.

Verification: separate real-Git RED commits, slug/immutable-ID persistence and commit
checks, unchanged primary bytes/index/HEAD, stale-spec mutation, unsafe selector and
dirty-checkout refusals, and focused recorder/implement regressions. This repairs
the tool needed by analyze; it does not manufacture an analysis verdict, approve
WP01, or authorize WP02, push, installation, or deployment.
