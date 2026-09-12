# Research: Owned-checkout seam for the task and status commands

Mission: `tasks-status-owned-checkout-seam-01M282V3` | Bead: `spk-8o2` | Issue: #26
Date: 2026-09-11

## Question

Why can `next`, `spec-commit` and `agent mission create` address a mission that lives in an owned
linked worktree while every command that records work-package state cannot, and what is the smallest
change that closes that gap without touching non-owned routing?

## Evidence base

**D-1 - the working pattern already exists.** `src/specify_cli/cli/commands/next_cmd.py` declares
`--owned-checkout`, wraps the command with `_require_main_repo_unless_owned` (which bypasses only the
syntactic `.worktrees` guard when the option is present), and in the body resolves the claim through
`resolve_ownership_claim(owned_checkout, resolved_primary=ambient_root)`; a refusal is rendered by
`_emit_checkout_ownership_error` and the command exits fail-closed. On success it uses
`claim.claimed_checkout` as the repo root and as the effective root. The same pattern is used by
`agent mission create` and `spec-commit`.

**D-2 - the ownership authority is shared and typed.** `src/specify_cli/core/checkout_ownership.py`
owns `OwnershipClaim`, `OwnershipValidationResult` (`OWNED`, `UNOWNED_NO_OPT_IN`, `NESTED`,
`FOREIGN_OR_MISMATCHED`, `BROKEN_POINTER`) and the typed error family, with `resolve_ownership_claim`
and `error_for_claim`. This is exactly the validation FR-003 asks for; no new validation may be
written.

**D-3 - the failing commands resolve their census from the ambient root.** `tasks_move_task.py` calls
`_tasks.locate_project_root()` and `tasks_shared.py` resolves the mission against that root;
`selector_resolution.resolve_mission_handle` hands the handle to `resolve_mission(handle, repo_root)`,
and `locate_project_root` is documented to return the **main** repository root from inside a worktree.
The owned mission therefore never appears in the census, and every selector form (slug, mid8, ULID)
returns `mission_not_found`.

**D-4 - `SPECIFY_REPO_ROOT` is not a workaround.** Setting it to the owned worktree still returns
`mission_not_found` because the resolver routes the value through `get_main_repo_root`, which collapses
a linked worktree back to the primary.

**D-5 - the write side is already parameterised by the root.** `coordination/status_transition.py`
derives its transaction identity from the `repo_root`, `feature_dir` and mission anchor carried on the
request, and `tasks_shared.py` places the status state through `placement_seam(main_repo_root,
mission_slug, kind=STATUS_STATE)`. Feeding the claimed checkout as that root is therefore a routing
decision, not a new writer (C-002).

**D-6 - an independent fix exists in flight.** Pull request 20 (mission
`linked-worktree-prerequisite-resolution-01M1MFE9`) carries `tasks_move_context.py` and
`test_move_task_owned_checkout.py` for `move-task`. A cherry-pick onto current `main` conflicts in
`status_transition._identity_for_request`, where that branch restructures the destination-ref
resolution. This mission must not resolve that conflict blindly (C-004); it implements the seam
through the shared ownership authority instead, and records the difference.

**D-7 - the previous mission's friction.** During
`sync-capture-coalescing-integrity-01M25WZF` the same gap stopped the runtime at `implement` with
`no actionable wp`, and `spec-kitty research` (no seam at all) wrote four scaffold files into the
protected primary checkout. Both are recorded in that mission's `traces/tooling-friction.md` on
`main`.

## Decisions

**RD-001 - reuse the ownership authority, add no new validation.** The new option resolves through
`resolve_ownership_claim` and refuses through `error_for_claim`, exactly like `next`.

**RD-002 - explicit declaration only.** No environment variable, cwd heuristic or ambient detection may
enable the seam (NFR-002). `SPECIFY_REPO_ROOT` gains no new meaning.

**RD-003 - the declared checkout becomes the repo root for the command.** Mission resolution, status
state placement and the transaction identity all read from the claimed checkout; nothing else about
routing changes.

**RD-004 - no-opt-in behaviour is byte-for-byte identical.** The opt-in branch is additive; the guarded
path stays as it is (C-001, FR-005).

**RD-005 - planning-side commands either honour the seam or refuse loudly.** Writing into the protected
primary for a mission that lives elsewhere is never an acceptable outcome (FR-006).

## Impact analysis

- `src/specify_cli/cli/commands/agent/tasks_move_task.py` and the shared task helpers: option
  plumbing plus claimed-root resolution.
- `src/specify_cli/cli/commands/agent/status.py`: the same option for `emit`, `validate`,
  `materialize` and `lifecycle`.
- Tests: a new owned-checkout acceptance suite plus additions to the existing move-task and status
  command suites.
- Unchanged: the ownership authority, the canonical status event log, the mission manifest, the sync
  layer, and every non-owned route.

## Open questions and risks

- **R-1**: whether the canonical status writer needs an explicit owned-mission route for
  `single_branch` topology or whether feeding the claimed root is sufficient. Resolved by the WP01
  acceptance test; if a route is needed it must reuse the existing writer (C-002).
- **R-2**: `tasks.md` checkbox updates and the WP frontmatter bootstrap must land in the owned
  checkout, not the primary.
- **R-3**: PR 20 may land first; the two approaches overlap in `move-task`. The mitigation is to keep
  this mission's change additive and to record the difference in the review trail.

## Addendum: the first implementation pass and the folds that remain

A first pass on `move-task` (option + validated claim + claimed root as the command's root, plus
skipping the primary fold in `_ensure_target_branch_checked_out`) moved the failure from
`mission_not_found` to a deeper refusal, which is itself the useful finding: **the resolution stack
folds a linked worktree back to the primary in more than one place**, and the command therefore needs
the owned root threaded further than the option surface.

Observed with the partial pass, run from this mission's own worktree:

```text
without --owned-checkout   -> {"error": "mission_not_found", "handle": "<slug>"}   (unchanged, parity held)
with    --owned-checkout   -> {"error": "meta.json not found for mission '<slug>' at
                               C:\\Users\\Ruslan\\spec-kitty\\kitty-specs\\<slug>"}
```

**D-8 - the remaining fold sites (all read the primary, none sees an owned root):**

- `src/mission_runtime/resolution.py:1027` (`primary_root = get_main_repo_root(repo_root)` in the
  topology-only resolver) and `:1083` in `mission_context_for`. The latter already accepts an
  **`effective_root`** and documents that folding an owned checkout through `get_main_repo_root`
  'would silently cross-read a sibling checkout (#3328 / C-002)' — this is the sanctioned seam and
  the one the remaining work must thread.
- `src/mission_runtime/lifecycle_phase.py:107, 264, 383` — the same fold in the lifecycle phase
  helpers.
- `src/specify_cli/missions/_read_path_resolver.py:1308` — `primary_dir = get_main_repo_root(repo_root)
  / KITTY_SPECS_DIR / mission_slug`.
- `src/specify_cli/coordination/surface_resolver.py:764` — `_compose_primary_feature_dir(repo_root, ...)`
  composed the primary path the final refusal named; this is the status-surface side of RD-003 and the
  reason R-1 is answered 'a route IS needed'.
- `src/specify_cli/cli/commands/agent/tasks_shared.py` `_find_mission_slug` legacy-dir probe
  (folds for an existence check only; harmless but part of the same family).

**Consequence for the plan**: WP01 is not an option-plumbing change. The seam must thread the
declared checkout as the **effective root** through `mission_context_for` and the surface resolver,
which is the same layer the in-flight PR 20 touches from the other direction (C-004). The working
method stays: keep the no-declaration path byte-identical (proved above), thread the effective root
through the sanctioned seam, and let the acceptance test decide when the seam is complete.

**D-9 - the concrete call chain that must carry the effective root.** Traced on this revision:

```text
move-task (tasks.py)
  -> _do_move_task -> _mt_resolve_targets (tasks_move_task.py)
       repo_root            = resolve_repo_root_with_owned_checkout(...)   # claimed checkout when declared
       main_repo_root       = _ensure_target_branch_checked_out(..., owned_root=repo_root)
  -> _mt_build_request   -> TransitionRequest(repo_root=..., ...)
  -> coordination/status_transition.py
       _identity_for_request  -> resolve_status_surface_with_anchor(repo_root, mission_slug)   # line 622
       _primary_anchor()      -> placement_seam(...).read_dir(PRIMARY_METADATA)
  -> coordination/surface_resolver.py
       resolve_status_surface_with_anchor -> _compose_primary_feature_dir(repo_root, slug)      # line 764
                                            |
                                            '-> folds the linked worktree back to the primary
```

The two functions that need an explicit **`effective_root`** parameter are therefore
`resolve_status_surface_with_anchor` and its thin wrapper `resolve_status_surface` (both currently
take only `repo_root`, `mission_slug`, `topology`), and the transition request must be able to carry
the declared checkout so `status_transition` and `_primary_anchor` stop folding. `mission_context_for`
already accepts `effective_root` (line 1083) and is the model for the parameter shape; the same
treatment is needed in `lifecycle_phase.py` (lines 107, 264, 383) and
`missions/_read_path_resolver.py:1308`.

This is the bounded implementation left for WP01: an additive `effective_root` parameter on the
surface resolver pair, carried on the transition request from the task command, with the
no-declaration path proved byte-identical.

**D-10 - the layer already owns the seam; its factory just does not expose it.** `mission_runtime
/resolution.py` threads an `effective_root` through `mission_context_for` (line 1085),
`resolve_action_context` (line 2224), the meta-path composer (line 225) and the fragment assemblers —
the whole layer is already built for an explicitly declared root. The fold survives because the
*factory* `placement_seam(repo_root, mission_slug)` (line 2198) and `PlacementSeam` itself do not
accept or carry it, so every caller that builds a seam from a bare root re-folds to the primary.

The remaining WP01 change is therefore, in the layer's own idiom:

1. `placement_seam(repo_root, mission_slug, *, effective_root=None)` forwarding into
   `PlacementSeam`, and `PlacementSeam` using it wherever it resolves an artifact home;
2. `resolve_status_surface` / `resolve_status_surface_with_anchor` gaining the same optional
   parameter and using `effective_root or repo_root` for `candidate_feature_dir_for_mission` and
   `_compose_primary_feature_dir`;
3. `TransitionRequest.effective_root` (status/models.py already defaults every field, so the
   addition is compatible) carried from the task command, used by
   `status_transition._canonical_primary_feature_dir` (line 564) for both its seam call and its
   resolver call;
4. the same treatment for `lifecycle_phase.py` and `missions/_read_path_resolver.py:1308` where
   they compose the primary dir from a bare root.

The no-declaration path stays byte-identical throughout, which the parity check in D-8 already
demonstrates for the option surface.

**D-11 - the fold bottoms out in one guarded leaf.** After threading `effective_root` through the
placement seam factory, `resolve_artifact_surface`, `resolve_placement_only`, both status-surface
resolver functions, `TransitionRequest` and `locate_work_package`, the owned run still ends in the
same refusal. A stack probe on the live CLI located the last fold:

```text
_mt_resolve_targets -> task_utils/support.locate_work_package -> surface_resolver.resolve_status_surface
  -> mission_runtime/_read_path_resolver._compose_primary_feature_dir   (line 1263)
       primary_dir = get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug   (line 1308)
```

`_compose_primary_feature_dir` is the terminal KITTY_SPECS join, and it folds **every** root it is
handed through `get_main_repo_root`; every layer above inherits that fold. The leaf documents itself
as permanent (C-004, never delete) and is machine-guarded: its sanctioned-import census lives in
`tests/architectural/test_no_read_side_bypass.py` (`_FOUNDATION_SANCTION_SEED` +
`_READ_SANCTIONED_MODULES`) and `tests/architectural/test_single_mission_surface_resolver.py` owns
the join. Closing issue 26 therefore has exactly two coherent shapes:

1. give that leaf an explicit owned-root parameter and update the two architectural censuses that
   sanction its callers (the seam this mission has already threaded is the correct upstream); or
2. adopt the placement-layer approach of the in-flight pull request 20, which changes
   `_read_path_resolver` and the task-context routing from the other direction (C-004).

Everything threaded so far is additive and verified non-regressive: `tests/mission_runtime/`, the
move-task orchestration suite and the compat-surface guard are **653 passed, 0 failed**, and the
no-declaration path still returns `mission_not_found` for an owned mission (parity held).

**Scope note**: the seam legitimately spans shared helpers outside the command files named in
`wps.yaml` — `task_utils/support.py` (the work-package locator), `mission_runtime/resolution.py`,
`coordination/surface_resolver.py` and `status/models.py`. WP01's `owned_files` must be widened to
name them, or the change is split across WPs; that is a plan edit, not a silent expansion.

**D-12 - the WRITE side still folds, and that is the next target (with a live demonstration).**
With the leaf carrying an owned root, the read side stopped folding entirely: the owned run resolved
the mission in the declared checkout and reached real business logic ("WP WP01 has no canonical
status … finalize-tasks"). Adding the same option to `agent status emit` then exposed the write side,
and it is a **hazard**, not a partial success:

```text
agent status emit WP01 --to planned --actor codex --owned-checkout <owned worktree> --mission <slug>
  -> {"wp_id": "WP01", "from_lane": "genesis", "to_lane": "planned",
      "status_events_path": "C:\\Users\\Ruslan\\spec-kitty\\kitty-specs\\<slug>\\status.events.jsonl"}
```

The event was written into the **protected primary checkout** (an untracked mission dir holding
`status.events.jsonl` and `status.json`) — exactly the FR-004 / C-003 violation this mission exists to
prevent. It was removed immediately; the primary is clean again (`git status` empty, HEAD
`78c1e9ab1`).

The folding chain is `status emit` -> `MissionStatus.load` -> `specify_cli/status/aggregate.py::
_find_meta_path` (line 545 `_compose_primary_feature_dir(repo_root, bare_dir_name)` and the
`resolve_bare_modern_mission_dir_name` call above it, line 550 `candidate_feature_dir_for_mission`)
-> the status writer/store. `MissionStatus` applies the primary fold before those calls, so the
declared checkout never reaches them.

**Actions taken instead of shipping a footgun**: the `agent status emit` option was reverted in full,
and `resolve_repo_root_with_owned_checkout` now fails closed with
`OWNED_CHECKOUT_WRITE_PATH_PENDING` for any declared checkout, so no command can currently write into
the primary through this seam. The resolution/read threading stays in place; lifting that gate is the
last step of WP01, after `MissionStatus` / `aggregate._find_meta_path` and the status store carry the
declared root the way the layers above now do.

**D-13 - the second pass sized the remaining work honestly.** Re-applying the WIP and reading the
write chain end to end produced the full bill for WP01. Beyond the read-side chokepoints this pass
already threaded, closing issue 26 still needs the declared root carried through:

1. `status/aggregate.py::MissionStatus.load` (line 190) — a new optional `effective_root` on the
   factory, propagated to every resolution it performs;
2. `status/aggregate.py::_read_meta` (line 398) — its `placement_seam(repo_root, mission_slug)`
   composition at line 509;
3. `status/aggregate.py::_find_meta_path` (line 460) — the `_compose_primary_feature_dir` (545) and
   `candidate_feature_dir_for_mission` (550) legs;
4. `status/aggregate.py::_resolve_read_dir` (line 290) and its delegator
   `missions/_read_path_resolver.py::resolve_surface_dir_or_typed_error` (line 1076);
5. the CLI-surface bill the option creates: 24 pinned guards turn red — the golden command-help
   fixtures (`test_tasks_cli_contract.py`), the `_MoveTaskArgs` field-set pin
   (`test_tasks_move_task_degod.py`), the seam-interception pin (`test_tasks_move_task_seam.py`), the
   json byte-identity pin (`test_tasks_json_bytes.py`), the pre-review observability pin and the
   compat-surface cardinality (171 -> 173).

Those 24 failures are the *expected, paid* cost of adding a CLI option in this repository, not design
work; but together with the four write-side chokepoints they are a dedicated session's worth, so the
WIP was re-parked rather than left half-landed with red guards and a gated feature.

**State of the branch after the second pass**: `src/` and `tests/` are byte-identical to
`origin/main` (`git diff origin/main -- src tests` is empty); the WIP commits remain in history
(`c627391c3`, `17b7edb03`, `e875c19f6`, `b6a8c5391`) and are restored with a single
`git revert 5dd8a5847`; the primary checkout is untouched. The mission's planning record plus
D-1..D-13 is the deliverable of these passes.

**D-14 - the write side is closed, and the closure is proven end to end.** The third pass carried the
declared root all the way through the write chain and lifted the fail-closed gate. Three folds still
collapsed it, and each was closed at the site that caused it:

1. `mission_runtime/write_target_degrade.resolve_write_target_or_degrade` (with its
   `_mission_meta_exists` pre-gate) resolved the placement against the ambient root, so an owned
   mission had no visible `meta.json` and the target degraded to the repo default - the protected
   primary branch - surfaced as `PROTECTED_BRANCH_REFUSED`. Both now take an optional
   `effective_root`.
2. `mission_runtime/resolution.resolve_placement_only` derived `target_branch` through
   `get_feature_target_branch`, which folds every root to the primary **by contract**. With a
   declared root it now reads the stored `target_branch` from that checkout and derives its
   fallback branch there, mirroring the opted-in arms already present at lines 1116 and 2299. The
   no-declaration arm is unchanged.
3. `coordination/status_transition._resolve_write_target` now threads the declared root into both
   the placement port and the `get_feature_target_branch` fallback, and `agent status emit`'s
   post-transition reload carries it too, so the reported `status_events_path` is the log the
   command actually wrote (D-12 recorded this path naming the protected primary).

A fourth, latent defect surfaced from the lint gate rather than from behaviour:
NaNcandidate_feature_dir_for_mission` had gained an `effective_root` parameter that the body never
consulted (ruff `ARG001`). Every caller above it therefore still resolved the ambient fold, and the
placement ref only came out right because its `resolve_primary_branch(placement_root)` fallback
happened to agree on this repository. On a repository whose primary branch differs from the mission’s
stored `target_branch` an owned run would have resolved the WRONG ref. With a declared checkout the
primitive now returns that checkout’s own mission directory when it exists there and keeps the historical
result when it does not, so the option can never invent an absent directory.

**Live proof (the acceptance run, from the protected primary’s own working directory).**

```text
primary cwd: C:\Users\Ruslan\spec-kitty   HEAD 78c1e9ab1, clean

agent status emit WP02 --to planned --actor codex \
  --mission tasks-status-owned-checkout-seam-01M282V3 \
  --owned-checkout <owned worktree> --json
  -> exit 0, event 01M291MDEQG9AXJHJ4X2VZ0BGA
  -> status_events_path = <owned worktree>\kitty-specs\<slug>\status.events.jsonl
  -> the event is the last line of THAT log
  -> primary HEAD unchanged, git status empty, no kitty-specs/<slug>/ in the primary

agent tasks move-task WP01 --to doing --owned-checkout <owned worktree> --json
  -> {"result": "success", "transition_applied": true, "new_lane": "in_progress",
      "path": "<owned worktree>\kitty-specs\<slug>\tasks\WP01-owned-checkout-seam.md",
      "status_events_path": "<owned worktree>\kitty-specs\<slug>\status.events.jsonl"}

the same move-task WITHOUT --owned-checkout, from the primary
  -> {"error": "mission_not_found", "handle": "tasks-status-owned-checkout-seam-01M282V3"}
     (exit 2 - the guarded path is unchanged, C-001)
```

The `OWNED_CHECKOUT_WRITE_PATH_PENDING` gate that parked this work in D-12 is lifted: the hazard it
guarded against is closed at the source, and the primary-unchanged assertions above are now machine-checked
in both oracles rather than observed by hand.

**The executable oracles (WP01 T001-T006).** Two new modules build a REAL owned checkout - a registered
linked worktree of a temporary primary, holding a real mission whose directory exists only there:
NaNtests/tasks/test_move_task_owned_checkout_seam.py` (4 tests) and
NaNtests/status/test_status_owned_checkout_seam.py` (3 tests). They assert the recorded lane sequence in the
owned log, the reported paths, that a refusal appends nothing, that a foreign directory is refused with a
typed error code, and that the primary’s HEAD and porcelain output are unchanged in every run.

**The local test bill, measured against a real baseline.** A clone of `main` (`78c1e9ab1`) was
built and the same suites run in it. At baseline on this Windows host the pinned guard files already fail
13 tests (11 golden `--help` fixtures that differ only in rich box-drawing characters, the
NaNlist-tasks` JSON byte-identity pin and the pre-review observability pin - all Windows path-
separator artifacts) and `tests/status/test_doctor_husks.py` fails 2 more. Those are unchanged by this
work. What this work cost, and has now paid: the `_MoveTaskArgs` field-set pin, the C-001 seam-
interception pin, the golden `move-task` help fixture, and two architectural ratchet descriptors
NaN(MissionStatus._find_meta_path` and the `_compose_primary_feature_dir` leaf) that anchor the exact
lines this seam re-wrote. The 12 `test_mission_setup_plan_phases` errors and the remaining failure set are
identical in the baseline clone.

**D-15 - the first CI round found three real gaps, and one of them is the defect itself.** The draft pull
request ran the POSIX shards this host cannot, and reported four failures. Three were the seam meeting
guards it had not yet been measured against, and the fourth was issue 26 appearing in a command that had
never been in scope:

1. `cutover-guard` (a required pre-merge check) refused the branch, because a mission living in an
   owned checkout is never cut over. Its own remedy is
   `spec-kitty migrate backfill-runtime-state --mission <slug>` - and that command could not run
   either: `_flip_phase` resolves the placement port primary home from the mission dir, the
   resolver folds the linked worktree back to the ambient primary, and the flip then failed closed with
   `PlacementMismatchError` naming a primary path that does not exist. The migration command now
   takes `--owned-checkout` (validated through the shared ownership authority) and threads an
   `effective_root` into `_resolve_primary_home_or_degrade` / `_flip_phase` /
   `cutover_mission`. This is the same defect class as the rest of the mission, found by a gate
   rather than by a user, and it is the honest reason the guard could not be satisfied by hand.
2. Four test doubles patched the seams this mission re-signed (`_compose_primary_feature_dir`,
   `candidate_feature_dir_for_mission`, `resolve_status_surface`,
   `_resolve_primary_home_or_degrade`) with fixed positional signatures and broke on the new
   keyword. They are widened to absorb it; none of their claims change.
3. The mission own WP prompt frontmatter carried `plan_concern_refs`, which the strict
   `WPMetadata` schema forbids - a direct symptom of these artefacts having been hand-written because
   `finalize-tasks` could not see the owned mission (D-1). Removed from both prompts and from
   `wps.yaml` so a regeneration cannot reintroduce it.

The mission is now genuinely cut over (`status_phase: "1"`) through the seam added in the same
commit, not by editing `meta.json` by hand. Four local shard runs reproduce the CI selections and
are green modulo the documented Windows baseline: missions fast 449 passed / 2 baseline failures, missions
integration 306 passed, status fast 995 passed / 2 baseline failures, migration 137 passed / 2 baseline
path-separator failures.

**D-16 - WP02 starts with one command that honours the seam and two that refuse it honestly.** The
planning-side package is explicitly honour-or-refuse (T007). The split landed as:

* `agent tasks list-tasks --owned-checkout <wt>` **honours** the declaration - it lists the owned
  mission\u2019s work packages, each path inside the declared checkout, and without the option the owned
  mission is still invisible (`mission_not_found`, exit 2 - parity held).
* `agent tasks finalize-tasks` and `agent tasks map-requirements` **refuse** it, before any read
  or write, with a typed message naming issue 26 and the commands that do honour it. Their write path runs
  through the WP02 ports, whose `MissionHandle` is a frozen `(repo_root, mission_slug)` pair whose
  readers fold a linked worktree to the ambient primary; carrying the declared root through that handle is
  the remaining piece of WP02, and refusing is the honest half of the contract until it lands.

All three gained the option, so the golden `--help` fixtures for those three commands were updated
alongside (the same pass that produced the `move-task` fixture). Verified live from the protected
primary\u2019s working directory: list-tasks listed WP01 (in_progress) and WP02 (planned) from the owned log
with owned paths; finalize-tasks exited 2 with the refusal and wrote nothing; the primary stayed clean.

**D-17 — обязательное покрытие на ae36eddc4 осталось ниже порога после исправления шардов.**
Прогон CI Quality https://github.com/rusliksu/spec-kitty/actions/runs/34697875221 завершился
с успешными запущенными тестовыми шардами и `cutover-guard`, но обязательный `diff-coverage`
показал 25 покрытых строк из 29 (86%, порог 90%). Не покрыты строки 1666–1667 и 1669–1670
в `src/mission_runtime/resolution.py`: чтение целевой ветки из метаданных объявленного checkout.
Общее покрытие diff 68% — отдельный рекомендательный показатель, не причина блокировки.

В `tests/mission_runtime/test_resolution_target_branch.py` добавлен параметризованный тест
публичного `placement_seam(..., effective_root=caller).write_target(kind)` для `RESEARCH` и
`STATUS_STATE`. Настоящий связанный worktree содержит миссию, отсутствующую в основном
checkout; её целевая ветка отличается и от `main`, и от текущей ветки worktree. Тест проверяет
целевую ветку и отсутствие изменений в основном checkout и метаданных миссии. Локально все
9 тестов файла прошли; каждая из четырёх строк имеет `hits=1` в отчёте coverage.
Независимое ревью дополнения замечаний не выявило.
Контрольная мутация в отдельном Python-процессе подменила чтение целевой ветки на `main`:
оба сценария упали на сравнении `main` с `codex/owned-mission-target` (2 failed).
Исходный код при этом не редактировался.

Тесты сохраняют маркер `git_repo`: это реальные Git-сценарии, а не `fast`-тесты без subprocess.
Их штатный шард `integration-tests-core-misc` измеряет `mission_runtime`, но пропускается
для draft без метки `ci:full` или `ready-for-ci`. Для окончательной проверки используется
предусмотренная метка `ci:full`; пороги, фильтры и исходный код не меняются.

Уточнение хронологии D-16: последующие коммиты уже реализовали поддержку объявленного
checkout для `finalize-tasks`, `map-requirements` и `research`; отказ двух первых команд,
описанный в D-16, относится к промежуточному состоянию ветки.

**D-18 — команда приёмки пока не видит owned-миссию.**
12 сентября 2026 года запуск кода этой ветки из её связанного worktree командой
`python -m specify_cli accept --mission tasks-status-owned-checkout-seam-01M282V3 --diagnose --json`
завершился с кодом 1 и `{"error":"mission_not_found","handle":"tasks-status-owned-checkout-seam-01M282V3"}`.
У `accept --help` нет опции `--owned-checkout`. Это отдельный оставшийся пробел: успешный CI
и снятие draft не являются доказательством успешной приёмки миссии. Её lifecycle не закрывается
и не исправляется вручную; `kitty-ops/lifecycle.jsonl` остаётся побайтно равным `origin/main`.

## Sources

`research/source-register.csv`, `research/evidence-log.csv`.
