---
work_package_id: WP03
title: Decision, Commit, and Workflow Closure
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: codex/check-prerequisites-task-worktree-resolution
merge_target_branch: codex/check-prerequisites-task-worktree-resolution
branch_strategy: Planning artifacts for this mission were generated on codex/check-prerequisites-task-worktree-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/check-prerequisites-task-worktree-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 3 - Write-side adoption and canary
history:
- at: '2026-09-03T20:41:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/decision.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- tests/specify_cli/cli/commands/test_decision_single_authority.py
- tests/specify_cli/cli/commands/test_safe_commit_cmd.py
- tests/tasks/test_linked_worktree_planning_context.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Decision, Commit, and Workflow Closure

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Complete the shared linked-worktree resolution contract for decision recording/verification and planning-artifact commits, then prove the original ancestry Mission can resume its tasks prerequisite gate without installing the candidate globally.

## Context and Constraints

- WP01 and WP02 must be approved; follow WP02's authority split exactly.
- Decisions must remain bound to canonical immutable Mission identity.
- Spec commits must still pass existing file containment, protection policy, and commit-router checks.
- Do not make write commands succeed by disabling protected-branch refusal.
- No active CLI installation, release, push, or primary-authoring fallback.
- The original ancestry Mission is a read/command canary, not an owned-file target.

## Branch Strategy

- **Strategy**: Continue the sequential lane after WP02.
- **Planning base branch**: `codex/check-prerequisites-task-worktree-resolution`
- **Internal merge target**: `codex/check-prerequisites-task-worktree-resolution`
- **External pull-request target**: fork `main`

Use only the WP03 lane workspace recorded in `lanes.json` when finalization becomes available.

```text
spec-kitty agent action implement WP03 --agent codex
```

## Subtasks and Detailed Guidance

### T009 — Adopt operation context in decision commands

**Purpose**: Restore governed planning questions for caller-owned Missions.

**Steps**:

1. Resolve repository root and Mission anchor through the canonical operation context.
2. Persist the canonical resolved slug/immutable identity, not the raw selector when they differ.
3. Read and write decision artifacts/status events at the selected Mission surface.
4. Preserve input-token validation, missing/ambiguous/conflict errors, idempotency, and local-only behavior.
5. Cover both open and verify flows used during specify/plan.

### T010 — Adopt operation context in spec-commit

**Purpose**: Commit planning artifacts from the owned task branch without misdiagnosing primary `main` as their surface.

**Steps**:

1. Select operation context before normalizing artifact file arguments.
2. Resolve relative paths against the selected Mission surface or validate absolute paths within it.
3. Keep `repository_root` for protection policy and commit routing inputs that truly describe Git topology.
4. Ensure the router targets the owned task branch for a single-branch caller-owned Mission.
5. Preserve actionable refusal for files outside the selected Mission and genuine protected-primary writes.

### T011 — Extend decision and commit-router regressions

**Purpose**: Prove write behavior is safe, not merely successful.

**Steps**:

1. Add focused slug and immutable-ID cases to existing decision single-authority tests.
   Use WP01's verified harness and commit the behavioral acceptance RED before the
   corresponding production fix; require the same success assertions GREEN at review.
2. Add linked-worktree placement and containment cases to safe-commit tests.
3. Assert cross-surface identity conflict refuses before any write.
4. Assert primary HEAD/status remain unchanged on success and failure.
5. Run the preserved decision/spec-commit success contract to green.
   Reconcile the existing mixed integration contract in the now WP03-owned
   `tests/tasks/test_linked_worktree_planning_context.py`: consume the verified
   harness without dropping or weakening any node's behavioral assertions. Record
   old-to-new node mappings if tests move. No skipped/xfail tests or inverted success
   conditions may substitute for repaired product behavior.

### T012 — Original-workflow canary and quality gate

**Purpose**: Demonstrate user-visible recovery and close the Mission evidence loop.

**Steps**:

1. Build/run the candidate from this task branch without installing it globally.
2. From `C:\Users\Ruslan\.codex-worktrees\spec-kitty-planning-artifact-ancestry-fix`, execute the exact resolver-returned prerequisite command for `planning-artifact-ancestry-fix-01M1K666`.
3. Require the returned absolute feature directory and task branch to match that worktree.
4. Confirm `C:\Users\Ruslan\spec-kitty` remains clean and its HEAD unchanged.
5. Run all focused suites, architectural guards, Ruff, strict mypy, compileall, and `git diff --check`.
6. Record evidence in the Mission/Bead; do not resume ancestry implementation until this repair is reviewed and integrated through the governed delivery path.
7. Enforce NFR-001 before WP03 approval and Mission acceptance: Windows and POSIX
   CI must run the complete focused test inventory on the same candidate SHA.
   Retain SHA, source/interpreter paths, exact commands, collected node IDs and
   passed/failed/skipped counts; require zero new platform-specific skips.
8. Check `.github/workflows/ci-quality.yml` / `integration-tests-core-misc` for
   `tests/tasks` coverage and the relevant command-suite jobs. Record actual
   run/job URLs and prove marker/shard selection did not omit the focused tests.
   Missing, skipped or unexecuted CI is pending, not PASS. No CI dispatch, push,
   workflow modification or environment installation is authorized by this WP.

## Test Strategy

```powershell
uv run --extra test pytest -q tests/tasks/test_linked_worktree_harness.py tests/tasks/test_linked_worktree_planning_context.py
uv run --extra test pytest -q tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/test_safe_commit_cmd.py
uv run --extra test pytest -q tests/tasks/test_planning_workflow_integration.py tests/tasks/test_check_prerequisites_surface_agreement.py
uv run --extra test ruff check src/specify_cli/cli/commands/decision.py src/specify_cli/cli/commands/spec_commit_cmd.py tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/test_safe_commit_cmd.py tests/tasks/test_linked_worktree_planning_context.py
uv run --extra test mypy --strict src/specify_cli/cli/commands/decision.py src/specify_cli/cli/commands/spec_commit_cmd.py
uv run python -m compileall -q src/specify_cli
git diff --check
```

## Definition of Done

- Decision open/verify and spec-commit satisfy the caller-owned contract.
- All structured refusal and containment controls remain green.
- The original tasks prerequisite canary succeeds against the candidate.
- Primary checkout is unchanged.
- Acceptance RED precedes the production fix and all focused suites are GREEN on the final WP03 commit; no filtered subset replaces the complete integrated contract.
- Windows and POSIX CI evidence for the same candidate SHA and focused test inventory is retained, with zero new platform-specific skips (NFR-001). Unavailable CI blocks approval and Mission acceptance.
- No runtime installation, push, PR, release, or deploy occurred within WP implementation.

## Risks and Mitigations

- **Risk**: File normalization escapes selected Mission. **Mitigation**: validate canonical resolved paths before router invocation.
- **Risk**: Protection policy is accidentally weakened. **Mitigation**: keep policy rooted in `repository_root` and preserve negative tests.
- **Risk**: Canary uses globally installed code. **Mitigation**: record the exact candidate invocation and version/source path.

## Review Guidance

Require proof of immutable identity binding, artifact containment, primary cleanliness, and the original-workflow canary. Reject any change that treats a protected-primary refusal as something to suppress globally.

## Activity Log

- 2026-09-03T20:41:12Z – system – Prompt created.
