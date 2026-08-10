---
work_package_id: WP09
title: Structural cohort B sanitation
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
- FR-007
- FR-008
- FR-014
- FR-016
- NFR-002
- NFR-003
- NFR-007
- NFR-009
- NFR-010
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
history:
- status: planned
  at: '2026-08-10T00:06:32Z'
  actor: codex
  note: Added after /spec-kitty.analyze exposed incomplete structural ownership
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP09.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp09-results.json
execution_mode: code_change
owned_files:
- tests/architectural/test_arch_shard_marker_completeness.py
- tests/architectural/test_artifact_selection_completeness.py
- tests/architectural/test_built_in_location_authority.py
- tests/architectural/test_charter_no_specify_cli_import.py
- tests/architectural/test_charter_runtime_canonical_paths.py
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_ci_fast_jobs_have_timeout.py
- tests/architectural/test_commit_target_kind_guard.py
- tests/architectural/test_coord_read_residuals_closeout.py
- tests/architectural/test_coord_rollback_coherence_guard.py
- tests/architectural/test_coverage_consumer_needs.py
- tests/architectural/test_cross_gate_churn_agreement.py
- tests/architectural/test_cross_grain_builtin_gate.py
- tests/architectural/test_dead_builtin_doc_paths.py
- tests/architectural/test_execution_context_parity.py
- tests/architectural/test_gate_coverage.py
- tests/architectural/test_git_matrix_paths_resolve.py
- tests/architectural/test_glossary_pack_boundary.py
- tests/architectural/test_glossary_pack_no_regression.py
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/test_job_count_ceiling.py
- tests/architectural/test_merge_pipeline_ratchets.py
- tests/architectural/test_merge_reconciliation_class_guard.py
- tests/architectural/test_migration_chain_integrity.py
- tests/architectural/test_mission_runtime_surface.py
- tests/architectural/test_no_dead_cli_paths.py
- tests/architectural/test_no_inert_schema_slots.py
- tests/architectural/test_no_op_stable_writes.py
- tests/architectural/test_no_phantom_worktree_repair.py
- tests/architectural/test_no_runtime_pypi_dep.py
- tests/architectural/test_org_activation_seam.py
- tests/architectural/test_patch_seam_census_control.py
- tests/architectural/test_plugin_validate_workflow.py
- tests/architectural/test_pyproject_shape.py
- tests/architectural/test_pytest_marker_convention.py
- tests/architectural/test_ratchet_positional_anchor_ban.py
- tests/architectural/test_read_surface_placement_guard.py
- tests/architectural/test_reference_enum_ratchet.py
- tests/architectural/test_resolution_activation_foundation.py
- tests/architectural/test_resume_non_reemission_guard.py
- tests/architectural/test_status_sync_boundary.py
- tests/architectural/test_surface_resolution_audit.py
- tests/architectural/test_tasks_command_surface.py
- tests/architectural/test_tid251_enforcement.py
- tests/architectural/test_trigger_registry_coverage.py
- tests/architectural/test_trio_seam_only.py
- tests/architectural/test_typer_compat_ci.py
- tests/architectural/test_untrusted_path_containment.py
- tests/architectural/test_urn_resolver_scalar_fence.py
- tests/architectural/test_workflow_dist_lint.py
- tests/architectural/test_wp_prompt_build_latency.py
- tests/architectural/test_write_surface_placement_guard.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP09.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp09-results.json
tags: []
tracker_refs:
- '#1931'
---

# WP09 — Structural Cohort B Sanitation

## Do First

Load `architect-alphonso`. Read FR-006/FR-007, the current ADR/contract authorities named by assigned files, WP01's structural candidate manifest, and WP05's survival rule. Claim through `spec-kitty agent action implement WP09 --mission assertive-test-suite-sanitation-01KZME3P --agent codex --profile architect-alphonso` and use only its worktree.

## Objective

Terminally adjudicate every assigned cohort-B structural file. Delete advisory-only, historical, positive-shape, prose/name/count, and migration-completion scaffolds that cannot catch a plausible current bug. Preserve a current negative invariant only when it scans a nonzero live corpus and fails at its intended oracle under a realistic authority violation.

## T051 — Complete Machine Screening

- Reconcile every owned path against WP01's generated structural manifest; missing/unowned paths stop for task replan before edits.
- Record scanner kind, corpus, positive vs negative shape, asserted oracle, referenced authority/issue, historical mission tokens, count/prose/name pins, and current CI role.
- Every assigned file gets a terminal screening verdict. Promote suspect survivors/deletions to deep rows; unchanged non-candidates need only the lightweight manifest row.
- Import/collection failure, an empty corpus, or pasting a searched literal does not prove causal bite.

## T052 — Delete Spent Scaffolds

- Delete files/tests whose only observable is historical layout, exact prose/token/name/count, completed migration shape, test self-presence, or non-failing advisory output.
- Remove file-local dead helpers/imports. Do not edit production behavior, shared shard maps, workflows, or another WP's surfaces.
- When a file mixes useful and spent checks, retain/rehome the smallest current negative invariant and delete the rest.
- Record deleted nodeids, authority absence, runtime/collection cost, and why no unique live boundary remains.

## T053 — Controlled Fault Proof

- For each deletion-justifying or materially changed survivor, name current authority, assert a nonzero corpus floor, and introduce a realistic prohibited source/AST/dependency change in a disposable copy.
- The Act must execute and intended assertion must fail. Collection/import/setup failures do not count.
- Use two-sided controls: compliant change remains green; prohibited change reds. Prefer focused deterministic fault injection to mutation theater.
- A survivor lacking proof is deleted unless HiC supplies a current authority and executable probe.

## T054 — Focused Validation and Ledger

- Run focused collection/tests for every surviving assigned file, `ruff` changed files, and focused mypy where helpers change.
- `WP09.yaml` gives every assigned file a terminal verdict and deep evidence only where the class profile requires it.
- Store commands, environment/hash, outcomes, costs, corpus size, fault result, and deleted/survivor node deltas in `wp09-results.json`.
- No skip/xfail/quarantine/flaky marker may be introduced to make a structural guard pass.

## T055 — Integration Handoff

- Emit a deterministic list of cohort-B deleted/renamed paths and required `_arch_shard_map.py` removals.
- Do not edit the central shard map. WP07 owns integration after WP03/WP04/WP05/WP09/WP10 complete.
- Commit owned changes and handoff. Full architectural hard-gate execution follows WP07 integration and repeats in WP08.

## Definition of Done

- [ ] Every assigned cohort-B file has a terminal structural verdict.
- [ ] Spent scaffolds are removed; no positive-shape implementation pin is renamed as an invariant.
- [ ] Every cited survivor has live corpus, current authority, and two-sided controlled-fault bite.
- [ ] Focused survivors pass; all deleted paths appear in deterministic integration handoff.
- [ ] Worktree clean after focused commit.

## Reviewer Guidance

Independently sample deletions and survivors. Reject “architectural” as authority, literal-paste probes, empty-corpus success, historical mission reports in pytest, count baselines without current budgets, and any edit outside owned files. Verify all owned paths reconcile to the ledger.

## Commit

`git commit -m "test(WP09): sanitize structural cohort b"`
