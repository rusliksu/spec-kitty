---
work_package_id: WP01
title: Verified Linked-Worktree Harness
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: codex/check-prerequisites-task-worktree-resolution
merge_target_branch: codex/check-prerequisites-task-worktree-resolution
branch_strategy: Planning artifacts for this mission were generated on codex/check-prerequisites-task-worktree-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/check-prerequisites-task-worktree-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Executable contract
history:
- at: '2026-09-03T20:41:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/tasks/
create_intent:
- tests/tasks/linked_worktree_harness.py
- tests/tasks/test_linked_worktree_harness.py
execution_mode: code_change
model: ''
owned_files:
- tests/tasks/linked_worktree_harness.py
- tests/tasks/test_linked_worktree_harness.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Verified Linked-Worktree Harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Deliver a reusable real-Git command/snapshot harness with its own RED-to-GREEN acceptance cycle. This WP claims harness correctness, not repaired planning consumers. Preserve immutable product RED evidence and hand off the unchanged success contracts to WP02/WP03. RED evidence alone never authorizes WP01 approval.

## Context and Constraints

- Read `../spec.md`, `../plan.md`, `../contracts/operation-context-consumer.md`, and `../quickstart.md` before editing.
- Context output is parity evidence for the specific verified action, not proof that every lifecycle consumer already works.
- Do not edit production files in this WP.
- Do not weaken or rewrite existing assertions to manufacture RED.
- Use a temporary primary repository plus a registered linked worktree; a plain copied directory is insufficient.
- Snapshot primary branch HEAD and working-tree status before every write-capable command.
- The Windows missing-`fcntl` origin-binding issue is out of scope.
- Do not modify the existing mixed product contract in `tests/tasks/test_linked_worktree_planning_context.py`; WP03 owns its final reconciliation. No xfail, skip, deleted success assertion or inverted expected exit code may make an unrepaired consumer look accepted.

## Branch Strategy

- **Strategy**: Single sequential code lane; WP01 precedes every production package.
- **Planning base branch**: `codex/check-prerequisites-task-worktree-resolution`
- **Internal merge target**: `codex/check-prerequisites-task-worktree-resolution`
- **External pull-request target**: fork `main`

When `lanes.json` is available, enter only the workspace allocated to WP01. Until bootstrap finalization is possible, remain in the validated task worktree and do not create an ad-hoc lane.

Implementation command after valid finalization:

```text
spec-kitty agent action implement WP01 --agent codex
```

## Subtasks and Detailed Guidance

### T001 — Build the linked-worktree Mission fixture

**Purpose**: Reproduce the topology that the existing unit tests miss.

**Steps**:

1. Create a temporary Git primary checkout with the minimum project markers required by `locate_project_root()`.
2. Commit the initial primary state and create a registered linked worktree on a distinct task branch.
3. Place a substantive Mission only in the linked worktree with valid `meta.json`, `spec.md`, `plan.md`, status log, and task scaffold as required by the invoked command.
4. Use a deterministic Mission slug and immutable ID so the same fixture can exercise both handle forms.
5. Provide helpers that capture primary HEAD, porcelain status, and Mission-tree contents before and after each command.

**Files**: `tests/tasks/linked_worktree_harness.py`, `tests/tasks/test_linked_worktree_harness.py`.

**Validation**: Prove Git recognizes the secondary checkout as a worktree and that the Mission is absent from primary.

### T002 — Drive harness acceptance RED-to-GREEN

**Purpose**: Verify the harness itself before downstream consumers rely on it.

**Steps**:

1. Before implementing the harness, commit acceptance checks that fail on its missing/incorrect behavior, not on syntax/import errors or an unrelated broken consumer.
2. Verify real worktree registration, requested cwd/arguments, returned exit code/stdout/stderr, and exact primary HEAD/index/file snapshot preservation with controlled local command inputs.
3. Use fixture literals as independent expected identities and paths, never the production resolver as both oracle and subject.
4. Implement the harness to make the complete harness suite GREEN. Keep product command invocations real in downstream tests; only unrelated external services may be mocked.
5. Mutate one expected Mission identity/path and deliberately alter a fixture primary file: the corresponding acceptance assertion must fail. Record these results; a green no-op or swallowed subprocess failure is not acceptable.

**Validation**: Full harness suite and existing operation-context controls pass on the final WP01 commit. Product success acceptance remains owned by WP02/WP03.

### T003 — Preserve RED evidence and behavioral handoff

**Purpose**: Preserve outside-in product contracts without mislabelling historical RED as final WP01 acceptance.

**Steps**:

1. Inventory the existing immutable RED commits and exact failing node IDs/reasons; do not amend or rewrite that history.
2. Map prerequisite/setup-plan success assertions to WP02's owned consumer suites and decision/spec-commit assertions to WP03's owned suites and final integrated contract.
3. Retain the expected success semantics, immutable identity, absolute selected path, branch, containment and primary-cleanliness assertions in the handoff.
4. Historical baseline reproduction is a diagnostic result, separate from the final harness acceptance result; record both honestly.
5. Each product WP must commit its acceptance RED before its corresponding code change and show unchanged assertions GREEN at review. Existing RED evidence may be reused only with verified exact base/node/reason provenance.

### T004 — Pin fail-closed and cleanliness controls

**Purpose**: Ensure caller preference cannot become unsafe fallback.

**Steps**:

1. Provide reproducible fixture inputs for missing, omitted-in-multi-Mission, ambiguous, unsafe/path-like and conflicting-identity cases.
2. Prove fixture identities really differ before asking downstream product tests to assert typed refusal.
3. Make the snapshot assertion execute on both successful and failed command returns.
4. Verify snapshots include tracked/untracked file bytes and index/status, not only HEAD; changes confined to the linked checkout must not falsely count as primary mutation.
5. Run the complete harness tests and diff-check. Keep the harness acceptance RED commit separate from its GREEN implementation commit.

## Test Strategy

```powershell
uv run --extra test pytest -q tests/tasks/test_linked_worktree_harness.py
uv run --extra test pytest -q tests/specify_cli/missions/test_operation_context.py
```

Both commands must be GREEN on the final WP01 commit. The new harness acceptance must have separate failing-first evidence on the planning base. The existing mixed product suite is still mandatory at the final Mission gate, not erased or declared passed by this scoped run.

## Definition of Done

- Four subtasks are represented by clear tests in the owned file.
- Harness acceptance has a separate RED commit and is GREEN at final review, without timing assumptions or platform-specific skips.
- Primary cleanliness and conflicting-identity controls are executable.
- No production file changed.
- Historical product RED and harness RED-to-GREEN evidence are recorded separately; no product completion is inferred.
- Identity/path and primary-mutation checks demonstrably reject incorrect inputs; an independent reviewer verifies the full harness deliverable.

## Risks and Mitigations

- **Risk**: Fixture bypasses `locate_project_root`. **Mitigation**: invoke actual CLI entry points from the registered worktree cwd.
- **Risk**: Write-capable tests leak state. **Mitigation**: isolate each case and snapshot both repositories.
- **Risk**: Tests couple to human error prose. **Mitigation**: assert structured codes and authoritative paths first.

## Review Guidance

Reject mock-only topology, missing immutable-ID cases, ineffective snapshot checks, or any attempt to hide pending product failures. Verify harness RED on its planning base and GREEN on its final commit before approving WP01. A RED-only product checkpoint is never an approval. WP02 still requires canonical WP01 approval; do not edit lifecycle events manually.

## Activity Log

- 2026-09-03T20:41:12Z – system – Prompt created.
