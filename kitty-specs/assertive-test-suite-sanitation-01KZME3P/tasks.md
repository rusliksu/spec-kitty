# Work Packages: Assertive Test Suite Sanitation

**Mission**: `assertive-test-suite-sanitation-01KZME3P`  
**Planning/merge branch**: `pr/assertive-test-suite-sanitation`  
**Protected PR base**: `main`  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Execution Shape

WP01 establishes reproducible census/evidence. WP02 repairs #3283. WP03 and WP06 depend on the healthy harness; WP04/WP05 can proceed from the census in parallel. WP07 folds the approved test topology into proportional CI. WP08 generates aggregate proof and closure artifacts. Each adjudication WP owns one ledger shard; only WP08 writes the generated aggregate.

## Subtask Index

| Subtask | Description | WP | Parallel |
|---------|-------------|----|----------|
| T001 | Implement mission-local AST/ignore discovery and pytest collection-hook snapshot | WP01 | No |
| T002 | Capture immutable base census and reconcile discovered/collected/zero-node units | WP01 | No |
| T003 | Freeze workload DAG, route universe, environment identity, and raw #3283 evidence | WP01 | Yes |
| T004 | Validate deep-shard schema, grouping divergence, class profiles, and temporary rules | WP01 | No |
| T005 | Prove auditor determinism and fail-closed behavior with temporary fixtures | WP01 | No |
| T006 | Commit compact raw artifacts/hashes and foundation evidence summary | WP01 | No |
| T007 | Add red concurrency tests for slow live builder and two fresh starters | WP02 | No |
| T008 | Add dead-owner, crash-mid-build, invalid-final, and PID-reuse tests | WP02 | Yes |
| T009 | Implement lease/heartbeat/temp-build/validation/atomic-publish state machine | WP02 | No |
| T010 | Prove macOS/Linux/Windows publication semantics and no half-built consumer | WP02 | No |
| T011 | Persist exact replay patch and run identical base/HEAD harness comparison | WP02 | No |
| T012 | Record three consecutive fresh-start results and WP02 disposition shard | WP02 | No |
| T013 | Census every unconditional skip, permanent xfail, quarantine, placeholder, and flaky marker | WP03 | No |
| T014 | Delete ten #2309 daemon-reaper skipped bodies and two #2316 upgrade skipped bodies | WP03 | Yes |
| T015 | Delete live-server placeholder and obsolete missing-ref/advisory skipped tests | WP03 | Yes |
| T016 | Adjudicate #2342 quarantine and root-cause/delete lingering flaky marker | WP03 | Yes |
| T017 | Preserve one live blocking #2782 red reproduction with no self-skip | WP03 | No |
| T018 | Complete class-specific inert-state shard with terminal verdicts | WP03 | No |
| T019 | Run focused and repeated state/marker validation with zero new masking | WP03 | No |
| T020 | Prove runtime/kernel home-path duplication and preserve unique Windows/import contracts | WP04 | Yes |
| T021 | Prove legacy/unit git-ops duplication and retain canonical live seam | WP04 | Yes |
| T022 | Consolidate duplicate dashboard glossary and lint handler suites | WP04 | Yes |
| T023 | Consolidate duplicate lane/template guards while preserving one negative invariant | WP04 | Yes |
| T024 | Run survivor causal/fault probes and focused mutation comparisons | WP04 | No |
| T025 | Record removed members, survivors, costs, and unique boundaries in WP04 shard | WP04 | No |
| T026 | Adjudicate never-fail retired-contract advisory and historical report validators | WP05 | Yes |
| T027 | Remove name/token/count/prose/self-presence scaffolds with no current authority | WP05 | Yes |
| T028 | Re-evaluate auth transport and batch-drain positive-shape guards against current ADRs | WP05 | Yes |
| T029 | Preserve/rehome only plausible-authority-violating negative invariants | WP05 | No |
| T030 | Update architectural shard/import/baseline consumers after deletions | WP05 | No |
| T031 | Record structural causal probes, dead-symbol caller proof, and WP05 verdicts | WP05 | No |
| T032 | Reproduce and classify every #3284 base failure/error under repaired harness | WP06 | No |
| T033 | Adjudicate doctrine reachability/count pins and charter compact-size threshold | WP06 | Yes |
| T034 | Adjudicate ANSI console and mission-template-resolution assertions | WP06 | Yes |
| T035 | Adjudicate timing, daemon, safe-commit, sync teardown, and E2E portability failures | WP06 | Yes |
| T036 | Run fixed flake matrix for nondeterministic candidates; no retry-to-green | WP06 | No |
| T037 | Preserve live known-red set and record stale/non-causal explicit deltas | WP06 | No |
| T038 | Complete WP06 shard and focused regression validation | WP06 | No |
| T039 | Replace whole-tree regression/quarantine marker discovery with explicit owned selectors | WP07 | No |
| T040 | Model one owner plus documented coverage/platform/hard-gate overlaps | WP07 | No |
| T041 | Update architectural workflow contracts without weakening red-main authority | WP07 | No |
| T042 | Execute route-manifest selection and three-run fixed-route timing comparison | WP07 | No |
| T043 | Record summed compute, critical path, mapping, and WP07 disposition evidence | WP07 | No |
| T044 | Generate canonical aggregate ledger and HEAD census from WP shards | WP08 | No |
| T045 | Generate before/after report, live known-red delta, causal/mutation matrix, and issue matrix | WP08 | No |
| T046 | Run full parallel suite, orphan sweep, ruff, mypy, and route/platform gates | WP08 | No |
| T047 | Run contract, architectural, and sibling cross-repository E2E hard gates | WP08 | No |
| T048 | Update durable test docs/changelog and complete tracer evidence | WP08 | No |
| T049 | Validate all success criteria, temporary states, tracker verdicts, and PR readiness | WP08 | No |

---

## WP01: Reproducible Census and Evidence Foundation (P1)

**Prompt**: `tasks/WP01-census-evidence-foundation.md`  
**Independent test**: two clean snapshots of the same tree are byte-identical after timestamp normalization; injected zero-node, ignored, errored, and divergent-parameter fixtures are all reconciled or fail closed.

### Included Subtasks

- [ ] T001 Implement mission-local AST/ignore discovery and pytest collection-hook snapshot (WP01)
- [ ] T002 Capture immutable base census and reconcile discovered/collected/zero-node units (WP01)
- [ ] T003 Freeze workload DAG, route universe, environment identity, and raw #3283 evidence (WP01)
- [ ] T004 Validate deep-shard schema, grouping divergence, class profiles, and temporary rules (WP01)
- [ ] T005 Prove auditor determinism and fail-closed behavior with temporary fixtures (WP01)
- [ ] T006 Commit compact raw artifacts/hashes and foundation evidence summary (WP01)

**Dependencies**: none.  
**Parallel opportunities**: T003 may proceed while census hooks are completed.  
**Risks**: collection recursion and giant evidence churn; use an in-process plugin, stable ordering, compact records, and no hand-authored unchanged-KEEP narratives.  
**Estimated prompt**: ~300 lines.

## WP02: Shared Test-Venv Bootstrap Reliability (P1)

**Prompt**: `tasks/WP02-test-venv-bootstrap.md`  
**Independent test**: slow live, dead, crashed, invalid, and simultaneous builders always publish one validated environment; no waiter observes a half-build; three fresh starts avoid #3283.

### Included Subtasks

- [ ] T007 Add red concurrency tests for slow live builder and two fresh starters (WP02)
- [ ] T008 Add dead-owner, crash-mid-build, invalid-final, and PID-reuse tests (WP02)
- [ ] T009 Implement lease/heartbeat/temp-build/validation/atomic-publish state machine (WP02)
- [ ] T010 Prove macOS/Linux/Windows publication semantics and no half-built consumer (WP02)
- [ ] T011 Persist exact replay patch and run identical base/HEAD harness comparison (WP02)
- [ ] T012 Record three consecutive fresh-start results and WP02 disposition shard (WP02)

**Dependencies**: WP01.  
**Risks**: deadlock, stale-owner theft, unsafe directory replacement, divergent replay patch.  
**Estimated prompt**: ~330 lines.

## WP03: Inert, Skipped, Quarantined, and Flaky States (P1)

**Prompt**: `tasks/WP03-inert-test-states.md`  
**Independent test**: global census has terminal verdicts for every inert state; permanent non-executing `KEEP` count is zero; #2782 remains exactly one live blocking red; no new masking marker exists.

### Included Subtasks

- [ ] T013 Census every unconditional skip, permanent xfail, quarantine, placeholder, and flaky marker (WP03)
- [ ] T014 Delete ten #2309 daemon-reaper skipped bodies and two #2316 upgrade skipped bodies (WP03)
- [ ] T015 Delete live-server placeholder and obsolete missing-ref/advisory skipped tests (WP03)
- [ ] T016 Adjudicate #2342 quarantine and root-cause/delete lingering flaky marker (WP03)
- [ ] T017 Preserve one live blocking #2782 red reproduction with no self-skip (WP03)
- [ ] T018 Complete class-specific inert-state shard with terminal verdicts (WP03)
- [ ] T019 Run focused and repeated state/marker validation with zero new masking (WP03)

**Dependencies**: WP01, WP02.  
**Parallel opportunities**: T014–T016 touch separate files.  
**Risks**: deleting the only P0 repro or treating conditional platform skips as permanent.  
**Estimated prompt**: ~350 lines.

## WP04: Duplicate and Compatibility-Shim Consolidation (P1)

**Prompt**: `tasks/WP04-duplicate-consolidation.md`  
**Independent test**: deleted duplicate members contribute no unique non-equivalent mutant, platform boundary, public import contract, or live path beyond the named survivor.

### Included Subtasks

- [ ] T020 Prove runtime/kernel home-path duplication and preserve unique Windows/import contracts (WP04)
- [ ] T021 Prove legacy/unit git-ops duplication and retain canonical live seam (WP04)
- [ ] T022 Consolidate duplicate dashboard glossary and lint handler suites (WP04)
- [ ] T023 Consolidate duplicate lane/template guards while preserving one negative invariant (WP04)
- [ ] T024 Run survivor causal/fault probes and focused mutation comparisons (WP04)
- [ ] T025 Record removed members, survivors, costs, and unique boundaries in WP04 shard (WP04)

**Dependencies**: WP01.  
**Parallel opportunities**: T020–T023 are independent surfaces.  
**Risks**: syntactic duplicates can guard distinct compatibility imports.  
**Estimated prompt**: ~330 lines.

## WP05: Structural and Spent-Scaffold Retirement (P1)

**Prompt**: `tasks/WP05-structural-scaffold-retirement.md`  
**Independent test**: every surviving structural guard scans a live nonzero corpus and fails under a plausible current-authority violation; removed guards pin only stale shape/prose/history or never fail.

### Included Subtasks

- [ ] T026 Adjudicate never-fail retired-contract advisory and historical report validators (WP05)
- [ ] T027 Remove name/token/count/prose/self-presence scaffolds with no current authority (WP05)
- [ ] T028 Re-evaluate auth transport and batch-drain positive-shape guards against current ADRs (WP05)
- [ ] T029 Preserve/rehome only plausible-authority-violating negative invariants (WP05)
- [ ] T030 Update architectural shard/import/baseline consumers after deletions (WP05)
- [ ] T031 Record structural causal probes, dead-symbol caller proof, and WP05 verdicts (WP05)

**Dependencies**: WP01.  
**Parallel opportunities**: T026–T028 begin independently; T029–T030 integrate.  
**Risks**: useful negative invariant embedded beside obsolete positive shape.  
**Estimated prompt**: ~350 lines.

## WP06: Pre-existing Red and Error Adjudication (P1)

**Prompt**: `tasks/WP06-baseline-red-adjudication.md`  
**Independent test**: all #3284 nodes receive reproducible classifications; live defects remain explicit; stale/non-causal failures are removed; base-green/HEAD-red count is zero.

### Included Subtasks

- [ ] T032 Reproduce and classify every #3284 base failure/error under repaired harness (WP06)
- [ ] T033 Adjudicate doctrine reachability/count pins and charter compact-size threshold (WP06)
- [ ] T034 Adjudicate ANSI console and mission-template-resolution assertions (WP06)
- [ ] T035 Adjudicate timing, daemon, safe-commit, sync teardown, and E2E portability failures (WP06)
- [ ] T036 Run fixed flake matrix for nondeterministic candidates; no retry-to-green (WP06)
- [ ] T037 Preserve live known-red set and record stale/non-causal explicit deltas (WP06)
- [ ] T038 Complete WP06 shard and focused regression validation (WP06)

**Dependencies**: WP01, WP02.  
**Parallel opportunities**: T033–T035 are separate clusters.  
**Risks**: confusing shared-fixture contamination with obsolete tests; product behavior fixes are out of scope.  
**Estimated prompt**: ~380 lines.

## WP07: Proportional CI Route Ownership (P2)

**Prompt**: `tasks/WP07-proportional-ci-routing.md`  
**Independent test**: changed narrow classes have exactly one owner route, documented secondary overlap, stable selection, and three-run cost comparison without whole-tree marker discovery.

### Included Subtasks

- [ ] T039 Replace whole-tree regression/quarantine marker discovery with explicit owned selectors (WP07)
- [ ] T040 Model one owner plus documented coverage/platform/hard-gate overlaps (WP07)
- [ ] T041 Update architectural workflow contracts without weakening red-main authority (WP07)
- [ ] T042 Execute route-manifest selection and three-run fixed-route timing comparison (WP07)
- [ ] T043 Record summed compute, critical path, mapping, and WP07 disposition evidence (WP07)

**Dependencies**: WP03, WP04, WP05, WP06.  
**Risks**: stranded tests, manufactured savings, or accidental quality-gate policy change.  
**Estimated prompt**: ~300 lines.

## WP08: Aggregate Evidence and Mission Closure (P1)

**Prompt**: `tasks/WP08-aggregate-closure.md`  
**Independent test**: generated aggregate validates; hard gates pass; known-red/issue matrices are exact; final report can be regenerated from shards/raw artifacts; all success criteria have evidence.

### Included Subtasks

- [ ] T044 Generate canonical aggregate ledger and HEAD census from WP shards (WP08)
- [ ] T045 Generate before/after report, live known-red delta, causal/mutation matrix, and issue matrix (WP08)
- [ ] T046 Run full parallel suite, orphan sweep, ruff, mypy, and route/platform gates (WP08)
- [ ] T047 Run contract, architectural, and sibling cross-repository E2E hard gates (WP08)
- [ ] T048 Update durable test docs/changelog and complete tracer evidence (WP08)
- [ ] T049 Validate all success criteria, temporary states, tracker verdicts, and PR readiness (WP08)

**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07.  
**Risks**: aggregate prose drifting from canonical evidence; report generation and checksums prevent dual authority.  
**Estimated prompt**: ~330 lines.
