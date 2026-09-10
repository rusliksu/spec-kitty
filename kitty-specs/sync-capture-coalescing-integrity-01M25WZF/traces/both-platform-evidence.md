# WP02: Both-platform evidence for the capture-fold repair

Mission: `sync-capture-coalescing-integrity-01M25WZF` (WP01 + WP02)
Bead: `spk-2ag`
Delivery: pull request 25 (base `main`)
Recorded: 2026-09-10

## Candidate revisions

| Revision | Commit | What it is |
|---|---|---|
| Code revision | `e35923636bb55d4ade81c8a211cb9179cc0dda42` | the WP01 repair (`src/specify_cli/sync/queue.py`) and its acceptance test |
| Delivery head at the recorded green run | `247831104` | code revision + the frozen-ledger restore (no code change: `git diff e35923636..HEAD -- src tests` is empty) |

Both platform runs below describe the same code revision; the only diff between them and the
delivery head is `kitty-ops/lifecycle.jsonl` being restored to its base bytes.

## RED -> GREEN (the behaviour, not the shard)

Acceptance test:
`tests/delivery/test_dispatcher.py::test_capture_after_a_drain_folds_without_an_orphan_outbox_task`.
It performs a real `dispatch()` (which installs the process-global coalescing seam exactly as
production does), then captures two events sharing one coalesce key through
`OfflineQueue.queue_event` **inside the same test body**, and asserts zero orphan outbox tasks,
exactly one journal row for the two identities, and `pending == queue.size() == 1`.

**RED before the repair** (code revision minus the guard):

```
tests/delivery/test_dispatcher.py::test_capture_after_a_drain_folds_without_an_orphan_outbox_task
  assert queue.queue_event(_coalescible_capture("cap-2")) is True
src/specify_cli/sync/queue.py:433
E   sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**GREEN after the repair**: `1 passed in 5.50s`.

**Mutation control**: the mutation is the one-line reversion of the guard (the unconditional
outbox insert). That reversion is exactly the state the RED run above was captured in, so the RED
output is the mutation evidence; no separate mutant run is needed and none was committed.

## Local evidence - native Windows (code revision `e35923636`)

Interpreter: the existing planning virtualenv
`C:/Users/Ruslan/.codex-worktrees/spec-kitty-check-prerequisites-task-worktree-resolution/.venv/Scripts/python.exe`,
candidate sources via `PYTHONPATH`, `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, plus the documented local
`fcntl` import shim (outside the repository; the base still imports `fcntl` unconditionally in
`sync/transport_lease.py`).

```
pytest -q tests/delivery/ tests/event_journal/ tests/sync/test_queue_resilience.py \
  tests/sync/test_offline_queue_counter.py
369 passed, 0 failed in 336.88s
```

Static gates on the changed files: `ruff check` passed, `mypy` clean, `compileall` clean,
`git diff --check` clean.

**Full `tests/sync/` selection on native Windows** was attempted with the same selection the CI
job uses. It is not carried to completion and is not evidence of anything about this mission:

- collection is blocked by `tests/sync/test_consent_fault_vocabulary_3030.py`, which calls
  `os.geteuid()` (POSIX-only; `AttributeError: module 'os' has no attribute 'geteuid'` on Windows).
  This is a pre-existing platform baseline, unrelated to this mission.
- after excluding that module the run reaches the transport / crash-matrix / revocation-matrix
  families, where native Windows has a large pre-existing failure population (the same class the
  dependent mission recorded as its Windows baselines: process-kill, fork and signal semantics).
  The run was stopped in that block; its counts are deliberately not presented as a result.

## POSIX evidence - cloud `CI Quality`

Run for the delivery head `247831104`:
<https://github.com/rusliksu/spec-kitty/actions/runs/34527842773> - **conclusion `success`**,
27 successful jobs, 0 failures, 36 skipped.

- `fast-tests-sync` job
  <https://github.com/rusliksu/spec-kitty/actions/runs/34527842773/job/103041099961>:
  `3043 passed, 2 warnings in 445.12s`, conclusion `success`. The same selection at the pre-repair
  head was `3 failed, 3040 passed` (run `34489743886`, job `102913159263`), and the three failures
  were exactly the capture-path nodes this mission repairs.
- aggregate `quality-gate` job
  <https://github.com/rusliksu/spec-kitty/actions/runs/34527842773/job/103046358203>:
  conclusion `success` - **no blocking verdict**. On `main` this gate had carried a blocking
  verdict continuously (first `fast-tests-sync`, later `arch-adversarial`).
- all three `arch-adversarial` shards: `success`.

### Intermediate run on the code revision (recorded because it is instructive)

Run `34525980265` at head `e35923636`: `fast-tests-sync` `success` (`3043 passed`), but the
aggregate gate `failure` with **one** blocking verdict: `arch-adversarial (arch_shard_1)` failing
`tests/architectural/test_archive_root_byte_identical.py::test_no_preexisting_archived_file_was_modified`
with `M kitty-ops/lifecycle.jsonl`.

Cause: the mission runtime appends to `kitty-ops/lifecycle.jsonl` and auto-commits its own op
bookkeeping on the mission branch, and that pre-existing file sits under one of the four immutable
exclusion roots (NFR-002: archived artifacts are byte-frozen). Remedy applied: the frozen ledger was
restored to its base bytes on the branch (`247831104`), leaving the per-op `kitty-ops/<ULID>.jsonl`
records - which are new files, not modifications - as the branch-local audit trail. The mission's
planning artifacts were moved into the mission dossier rather than the archive.

## What a green shard does and does not prove

`tests/sync/conftest.py` resets the process-global coalescing seam around every sync test
(`_reset_event_journal_coalescing_seam`, from `a84b110a7`). That makes the shard deterministic and
order-independent, but it also means **a green `fast-tests-sync` alone would not prove the capture
path is repaired**: with the seam reset there is nothing to fold. The repair is therefore evidenced
by the RED/GREEN acceptance test above, which drives the drain and the capture in one test body, and
the shard green is the corroborating platform evidence - not the proof.

## Residual gate

None inside this mission's owned files. Every remaining failure class named above is a pre-existing
platform baseline (`os.geteuid` POSIX-only module, native-Windows process/fork families) and none of
them is candidate-owned.

Hand-off: mission `linked-worktree-prerequisite-resolution-01M1MFE9` recorded the sync shard as its
residual blocker for WP03/T012. With `fast-tests-sync` and the aggregate quality gate both green at
the delivery head, that blocker is closed on the delivery surface; the dependent mission still owns
its own acceptance decision.
