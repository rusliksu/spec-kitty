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

### IC-01 — RED linked-worktree contract

- Build a reusable real-Git fixture with a Mission present only in a registered linked task worktree.
- Reproduce exact slug and immutable ID success expectations for prerequisites.
- Reproduce parity expectations for setup-plan, decision open/verify, and spec-commit.
- Assert primary checkout remains byte-clean and commit-clean.
- Preserve missing, omitted, ambiguous, traversal, and conflicting-identity failures.

### IC-02 — Read-side planning consumers

- Route `check-prerequisites` and `setup-plan` through `MissionOperationContext`.
- Keep repository-root preflight/protection checks anchored to the canonical primary repository.
- Resolve/read Mission artifacts through `mission_anchor_root` and canonical identity.
- Remove or bypass only the now-redundant primary-only selection inside those command paths.

### IC-03 — Decision and planning-commit consumers

- Route decision open/verify and spec-commit placement through the same operation context.
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

## Complexity Tracking

No constitution violation or new abstraction is planned. The existing operation-context seam is the intended consolidation point.
