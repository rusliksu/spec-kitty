---
work_package_id: "WP02"
title: "Both-platform evidence closure"
dependencies:
  - WP01
requirement_refs:
  - FR-004
  - FR-006
  - NFR-001
  - NFR-002
  - C-001
  - C-003
subtasks:
  - T007
  - T008
  - T009
  - T010
owned_files:
  - "kitty-specs/sync-capture-coalescing-integrity-01M25WZF/traces/**"
authoritative_surface: "kitty-specs/sync-capture-coalescing-integrity-01M25WZF/traces/"
execution_mode: "planning_artifact"
planning_base_branch: codex/sync-capture-coalescing
merge_target_branch: codex/sync-capture-coalescing
branch_strategy: Planning artifacts for this mission were generated on codex/sync-capture-coalescing. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/sync-capture-coalescing unless the human explicitly redirects the landing branch.
---

# Work Package Prompt: WP02 – Both-platform evidence closure

## Objective

Close the mission with reproducible evidence at one candidate SHA on native Windows and on
POSIX CI: the complete sync selection green, no new skips, and the aggregate quality gate
without a blocking verdict. Record it in a canonical trace and hand the result to the
dependent mission.

## Context

**Why this exists.** NFR-001 requires the same candidate SHA to be green on both platforms.
The sync shard has historically failed for a mixture of causes (a pinned dead unit of work,
a platform-specific daemon oracle, and this mission's capture-path defect), and at least one
of those was previously "fixed" for CI by isolating the process-global seam per test rather
than by repairing the capture path. Evidence must therefore name the exact SHA, the exact
selection, the interpreter, and the node counts, and must distinguish a green shard from a
repaired behaviour.

**What is already true on `main` (`78c1e9ab1`)**: the resolver-based seam (FR-004) with a
drain-then-capture regression test in `tests/delivery/test_dispatcher.py`; the
platform-hermetic daemon isolation oracle (FR-006); the per-test seam reset fixture in
`tests/sync/conftest.py`.

**Read first**: `spec.md` (NFR-001, NFR-002, SC-002, SC-005), `plan.md` (IC-03),
`research.md` (D-7, R-4).

## Subtasks & Detailed Guidance

### Subtask T007 – Local Windows selection at the candidate SHA

- **Purpose**: produce the native-Windows half of NFR-001.
- **Steps**:
  1. From the mission worktree, run the sync selection with
     `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and the documented local `fcntl` import shim (the
     base still imports `fcntl` unconditionally in `sync/transport_lease.py`; the shim
     lives outside the repository and is never committed).
  2. Record: interpreter path, candidate SHA (`git rev-parse HEAD`), the exact pytest
     command, and the passed/failed/skipped/deselected counts.
  3. List every failing node with its reason and classify it as candidate-owned or a
     documented platform baseline. A candidate-owned failure blocks the mission.
- **Files**: none in the repository; outputs feed T009's trace.
- **Validation**: counts and node names are copy-pasteable from the run.
- **Parallel?**: No.

### Subtask T008 – POSIX CI at the exact SHA

- **Purpose**: produce the POSIX half of NFR-001 from the published surface.
- **Steps**:
  1. Push the mission branch and open the delivery pull request to `main` (draft is
     acceptable while verification is running; ready/merge are separate decisions).
  2. Identify the `CI Quality` run for the exact candidate SHA and read the
     `fast-tests-sync` job: conclusion plus the final count line.
  3. Read the aggregate `quality-gate` job's blocking verdicts. Any verdict other than
     "none" must be attributed to a node outside this mission's owned files, with its own
     evidence line.
  4. If the run is red on a candidate-owned node, stop and return to WP01 rather than
     recording a partial result.
- **Files**: none in the repository; outputs feed T009's trace.
- **Validation**: run URL, job URL, job id, head SHA and the count line are all recorded.
- **Parallel?**: No.

### Subtask T009 – Canonical evidence trace

- **Purpose**: put the evidence where the pipeline and the dependent mission can read it.
- **Steps**:
  1. Write `kitty-specs/sync-capture-coalescing-integrity-01M25WZF/traces/both-platform-evidence.md`
     containing: candidate SHA; the RED and GREEN outputs from WP01's acceptance test; the
     mutation-check result; the local Windows counts; the POSIX job conclusion and count
     line; the quality-gate verdicts; and an explicit statement of what a green shard does
     and does not prove given the per-test seam reset.
  2. Append the same facts to the mission Bead `spk-2ag` (append-only note).
  3. State the residual gate explicitly if anything is still red outside the mission.
- **Files**: `traces/both-platform-evidence.md` (~80-120 lines).
- **Validation**: every claim in the trace carries a command, a URL or a job id.
- **Parallel?**: No.

### Subtask T010 – Hand-off to the dependent mission

- **Purpose**: close the loop that motivated this repair.
- **Steps**:
  1. Record the result for mission `linked-worktree-prerequisite-resolution-01M1MFE9`
     (WP03/T012 residual gate): its sync baseline blocker is closed or explicitly scoped,
     with the exact PR/run URLs.
  2. Do not modify that mission's artifacts in this WP; report the facts and let its own
     workflow record them.
- **Files**: none (reporting only).
- **Validation**: the hand-off names the exact URLs and the remaining gate, if any.
- **Parallel?**: No.

## Definition of Done

- A candidate SHA is named once and used by every evidence line.
- Local Windows and POSIX results are recorded with commands, counts, URLs and job ids.
- Every remaining failure is classified and none of them is candidate-owned.
- `traces/both-platform-evidence.md` exists and the Bead carries the same facts.
- No new skip, xfail or deselection appears in either platform's evidence.
- The hand-off to the dependent mission states the exact residual gate.

## Risks

- **Green-by-isolation**: a green shard after the per-test seam reset is not proof of the
  repair; the trace must pair it with WP01's acceptance test and mutation check.
- **Platform baselines**: Windows-only failures (for example the POSIX-only path oracle
  class) must be listed as baselines, never silently excluded from the counts.
- **Base drift**: if `main` moves again, re-run the evidence at the new SHA rather than
  reusing counts from an older one.
- **Scope creep**: this WP produces evidence and reporting only; it must not edit product
  code or the dependent mission's artifacts.

## Reviewer Guidance

Focus on: (1) is the SHA consistent across every evidence line; (2) are counts and job ids
copy-pasteable rather than summarised; (3) is the distinction between "shard green" and
"behaviour repaired" stated explicitly; (4) are residual failures classified with their own
evidence; (5) does the hand-off give the dependent mission an actionable verdict. Reject a
trace that claims a repair without the acceptance-test and mutation evidence.
