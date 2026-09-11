# WP01 / WP02 review verdicts

Mission: `sync-capture-coalescing-integrity-01M25WZF`
Delivery: pull request 25, head `d7e55c608`, CI Quality run `34529684069` (`success`)
Reviewer: codex (author-side review; an independent human verdict remains the merge gate)
Recorded: 2026-09-11

## Why this file exists in this shape

The runtime review surface (`spec-kitty agent tasks move-task`, `spec-kitty agent status emit`)
could not be used for this mission: every selector form returns
`{"error": "mission_not_found"}` because that command family resolves its mission census from
the project root checkout, and this mission lives only in the owned linked worktree
(`C:\Users\Ruslan\.codex-worktrees\spec-kitty-sync-capture-coalescing`). The same commands were
run with the slug, the mid8 and the full ULID, and with `SPECIFY_REPO_ROOT` pointed at the
worktree; all returned `mission_not_found`. `spec-kitty next` and `spec-kitty spec-commit`
do work because they accept `--owned-checkout`; the task and status command families have no
such seam in this revision.

Consequences, stated plainly:

- **No lane transition event was emitted.** WP01 and WP02 remain in the `planned` lane; their
  approval is recorded here as a reviewed verdict, not as a canonical `review_result` event.
- The mission therefore cannot advance past `implement` in the runtime until either
  (a) pull request 20 (mission `linked-worktree-prerequisite-resolution-01M1MFE9`, which carries
  the owned-checkout mission routing for `move-task`) lands, or (b) the task/status command
  families gain the `--owned-checkout` seam that `next` and `spec-commit` already have.

This is a tooling gap, not a work-package defect; it is recorded in
`traces/tooling-friction.md` with the exact reproduction.

## WP01 - Capture fold integrity: **APPROVE**

Reviewed artefact: code revision `e35923636`, files `src/specify_cli/sync/queue.py`,
`tests/delivery/test_dispatcher.py`, `tests/sync/test_queue_resilience.py`,
`tests/sync/test_offline_queue_counter.py`.

| Definition of Done | Evidence | Verdict |
|---|---|---|
| T001 acceptance test exists and reproduces RED before the change | `sqlite3.IntegrityError: FOREIGN KEY constraint failed` at `sync/queue.py:433`, captured at the pre-fix revision | Met |
| T001 turns GREEN after the change | `1 passed in 5.50s`; corroborated by CI | Met |
| The capture writes an outbox task only for identities the journal stored | the fold sentinel guard (`inserted=False`, `capture_sequence=0`, `epoch_id=0`) returns before the insert; diff is 9 added lines in one module | Met |
| Fold writes nothing and reports success | acceptance test asserts zero orphan tasks, one journal row for two identities, `pending == queue.size() == 1` | Met |
| Delivery/journal/queue suites green on Windows | `369 passed, 0 failed` | Met |
| Static gates clean | `ruff`, `mypy`, `compileall`, `git diff --check` | Met |
| No new skip / xfail / deselection | diff adds none; the two sync files changed prose and a comment only (`+13/-2`, `+3`) | Met |
| Mutation control | the pre-fix RED run is the mutation (one-line reversion of the guard) | Met |

Scope check: the delivery diff touches 4 files under `src/` and `tests/`, none outside WP01's
`owned_files`; no schema, seam, ledger, dispatcher or policy change is present.

## WP02 - Both-platform evidence closure: **APPROVE**

Reviewed artefact: `traces/both-platform-evidence.md`, bead `spk-2ag` notes.

| Definition of Done | Evidence | Verdict |
|---|---|---|
| One candidate SHA used by every evidence line | code revision `e35923636`; delivery head `247831104` / `d7e55c608`; `git diff e35923636..HEAD -- src tests` is empty | Met |
| Local Windows result recorded with command and counts | `369 passed, 0 failed` (targeted set), exact command in the trace | Met |
| POSIX result recorded with job ids and counts | run `34529684069`; `fast-tests-sync` job `103047184451` = `3043 passed`; `quality-gate` job `103052480010` = `success` | Met |
| Every remaining failure classified | POSIX-only `os.geteuid` module and the native-Windows process/fork families, both pre-existing and named | Met |
| Green shard is not presented as proof of the repair | the trace carries a dedicated section on the per-test seam reset | Met |
| Bead carries the same facts | two append-only notes on `spk-2ag` | Met |
| Hand-off to the dependent mission | stated in the trace and the bead: the sync shard and quality gate are green at the delivery head | Met |

Residual risk accepted by the reviewer: the full `tests/sync/` selection was not carried to
completion on native Windows (pre-existing platform families), so the Windows half of NFR-001 is
evidenced by the targeted set plus the POSIX shard, not by a full Windows shard. This is recorded
rather than hidden.

## Remaining gates (human)

1. Lane/verdict events for WP01 and WP02 - blocked by the owned-worktree resolution gap above.
2. Mission `accept` and the merge of pull request 25 - a human decision.
