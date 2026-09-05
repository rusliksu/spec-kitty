# Owned planning allocation recovery — 2026-09-05

Mission: `linked-worktree-prerequisite-resolution-01M1MFE9`; Bead: `spk-1m6`.
Scope: the approved allocation/reuse/claim bootstrap, not WP01 harness completion.
Worktree: `C:/Users/Ruslan/.codex-worktrees/spec-kitty-check-prerequisites-task-worktree-resolution`.
Branch: `codex/check-prerequisites-task-worktree-resolution`.

## Implementation boundary

`MissionOperationContext` retains separate repository and artifact roots. Fresh
allocation additionally proves Git registration, same repository, caller root,
immutable Mission selection and the declared planning branch, and refuses dirt.
The public materializer and internal allocation command both apply this check;
the global primary-only decorator is unchanged. Explicit `--recover` remains
primary-only. Existing lane retry still permits the same WP's uncommitted work.

The selected anchor reaches WP/manifest/status reads, allocation topology,
self-heal, ancestry and claim commit placement. Canonical Git/lane placement and
the existing workspace registry remain repository-root-owned. Commit routing
uses `mission_context_for`, not a guessed branch or relaxed protected-ref guard.

## Executed evidence

- RED commit `5c664790a`: both real public CLI cases (slug and immutable ID)
  refused with `Workspace does not exist and cannot be created from a worktree`.
- Intermediate real-Git GREEN: 9 cases passed, including nested-cwd retry with
  dirty lane preservation, one claim, recorded planning ancestry, repository-only
  workspace registry, dirty caller, foreign branch, missing/corrupt manifest,
  husk, conflicting immutable identity and an unregistered copied checkout.
- Existing allocation/claim/checkout/recovery suites: 154 passed. Additional
  coordination routing and runtime-frontmatter/VCS-lock suites: 47 passed.
- A temporary acceptance-data mutation changed the expected recorded base to
  `codex/wrong-base`. The immutable-ID test failed specifically on the actual
  registry value (`codex/task`), not fixture setup or command failure. Restored.
- The final fixture also exercises a distinct mission integration branch and
  the first VCS-lock write, matching the real Mission's single-branch topology.
- Ruff, strict mypy (9 explicit source inputs, including `core/errors.py` to
  preserve `StructuredError` types under import skipping), compileall and
  `git diff --check` passed before the final combined run.

All tests use the task's `.venv/Scripts/python.exe` and source checkout; temporary
real Git repos live under unique `C:/Windows/Temp/spk-*` basetemps, outside HOME.
Fixture-local `core.longpaths=true` supports the nested Windows lane paths; no
global configuration or assertion was weakened.

## Separate Windows limitation (not waived)

The adjacent `tests/lanes/test_issue_2993_lane_planning_ancestry.py` run had two
failures (legacy-fallback and placement-ref) in coordination atomic writes.
`_open_confined_parent_fd` requires POSIX `dir_fd`, `O_DIRECTORY` and `O_NOFOLLOW`.
All three are unavailable in this Windows interpreter. Executing that primitive
from the unchanged `5c664790a` Git blob independently reproduced the same refusal
before any write. This package does not change `coordination/atomic_write.py`,
disable the guard, add skips or claim cross-platform acceptance.

These baseline failures remain a final Mission verification issue. POSIX CI and
same-SHA Windows/POSIX acceptance are pending; no WP approval is implied.

## Final verification / real Mission canary

Final combined run: **210 passed, zero failed/skipped**, 193.40 seconds. It ran
the complete new test file and all 13 regression files listed by the preceding
154/47 groups, with no `-k` filtering. Guarded live invocation is next. No real
lane or claim has been created at this checkpoint. Primary remains clean at
`6befd9b43174b9f2c117f8bc02443001c9c25cb6`; the real event-log SHA256 is unchanged:
`0BA37C340B47384093A1A6C29A3B674446BAA5DC72460294711DA6C93E2D5FDF`.
