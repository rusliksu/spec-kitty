---
work_package_id: WP10
title: Structural cohort C sanitation
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
- T056
- T057
- T058
- T059
- T060
history:
- status: planned
  at: '2026-08-10T00:06:32Z'
  actor: codex
  note: Added after /spec-kitty.analyze exposed incomplete structural ownership
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP10.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp10-results.json
execution_mode: code_change
owned_files:
- tests/architectural/test_activation_registry_schema.py
- tests/architectural/test_all_declarations_required.py
- tests/architectural/test_arch_pole_deserialized.py
- tests/architectural/test_builtin_override_policy.py
- tests/architectural/test_charter_sole_door_agent_profile_repository.py
- tests/architectural/test_charter_sole_door_doctrine_service.py
- tests/architectural/test_charter_sole_door_hardcoded_paths.py
- tests/architectural/test_charter_sole_door_inner_reacharound.py
- tests/architectural/test_charter_sole_door_resolver_imports.py
- tests/architectural/test_cli_console_single_seam.py
- tests/architectural/test_docs_scoped_arch_coverage.py
- tests/architectural/test_dossier_sync_boundary.py
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/test_events_tracker_public_imports.py
- tests/architectural/test_gate_coverage_parse_model.py
- tests/architectural/test_gate_read_literal_ban.py
- tests/architectural/test_glossary_canonical_terms.py
- tests/architectural/test_glossary_pack_parity.py
- tests/architectural/test_glossary_pack_urn.py
- tests/architectural/test_golden_count_ban.py
- tests/architectural/test_guard_capability_call_sites.py
- tests/architectural/test_innerstatechanged_invariants.py
- tests/architectural/test_kernel_no_doctrine_import.py
- tests/architectural/test_mission_resolver_walker_gate.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_no_primary_anchored_gates.py
- tests/architectural/test_no_production_worktree_guard_bypass.py
- tests/architectural/test_no_prompt_filtering_added.py
- tests/architectural/test_no_shipped_layer_label.py
- tests/architectural/test_no_tmp_paths_in_tests.py
- tests/architectural/test_no_worktree_name_guess.py
- tests/architectural/test_pre_review_scope_singlesource.py
- tests/architectural/test_profile_load_resolver_guidance.py
- tests/architectural/test_protection_resolver_call_sites.py
- tests/architectural/test_pytest_marker_correctness.py
- tests/architectural/test_real_home_isolation_guard.py
- tests/architectural/test_safe_commit_import_boundary.py
- tests/architectural/test_safety_registry_completeness.py
- tests/architectural/test_same_tier_uniqueness.py
- tests/architectural/test_serial_port_preservation.py
- tests/architectural/test_tasks_domain_gate_visibility.py
- tests/architectural/test_template_governance_payload_contract.py
- tests/architectural/test_ui_e2e_coverage_discovered.py
- tests/architectural/test_unfiltered_journal_read_boundary.py
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/test_verdict_vocab_single_source.py
- tests/architectural/test_worktrees_index_clean.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP10.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp10-results.json
tags: []
tracker_refs:
- '#1931'
---

# WP10 — Structural Cohort C Sanitation

## Do First

Load `architect-alphonso`. Read FR-006/FR-007, current governance/security/CI authorities referenced by assigned files, WP01's structural manifest, and WP05's survival rule. Claim through `spec-kitty agent action implement WP10 --mission assertive-test-suite-sanitation-01KZME3P --agent codex --profile architect-alphonso` and use only its worktree.

## Objective

Terminally adjudicate every assigned cohort-C structural file. This cohort contains high-authority governance and safety guards, so deletion remains assertive but evidence-led: remove stale positive shape/history/prose/count scaffolds; retain only live negative invariants with plausible controlled-fault bite.

## T056 — Complete Machine Screening

- Reconcile every owned path against WP01's structural candidate manifest; unowned discoveries trigger pre-dispatch task replan.
- Capture scanner kind, corpus, asserted oracle, positive/negative shape, named current authority, current consumer/route, historical tokens, and count/name/prose pins.
- Every assigned file receives a terminal screening verdict. Promote suspect files into deep adjudication; unchanged non-candidates retain only lightweight machine rows.
- Explicitly distinguish active security/governance boundaries from assertions that merely demand exact module names or completed migration layout.

## T057 — Delete Spent Scaffolds

- Delete advisory-only, historical report/WP, positive implementation-shape, exact prose/name/count, and self-presence checks without current authority.
- Preserve useful negative checks from mixed files by reducing to the smallest behaviorally meaningful oracle.
- Do not edit route-owned `test_ci_quality_path_filters.py`/`test_suite_jobs_gate_blocking.py`, WP04-owned shim registry, or WP05-owned migration clusters; their exact owners terminalize them.
- Remove only owned dead helpers/imports; no product behavior changes.

## T058 — Controlled Fault Proof

- For each deletion-justifying or materially changed survivor, record authority, nonzero corpus, a realistic prohibited change, Act reached, and intended assertion failure.
- Require compliant control green and prohibited control red. A parser error, missing import, collection failure, or pasted literal is invalid proof.
- Prefer narrow fault injection; use focused mutation only where it adds non-equivalent causal evidence.
- If a current high-authority invariant cannot be proven cheaply, preserve it provisionally only by escalating to HiC before terminal verdict; do not silently delete or mark temporary.

## T059 — Focused Validation and Ledger

- Run focused collection/tests for every surviving assigned file, `ruff` changed files, and focused mypy for changed helpers.
- `WP10.yaml` maps every assigned file to a terminal verdict; `wp10-results.json` stores commands/env/hash/outcomes/costs/corpus/fault deltas.
- No masking markers, retry-to-green, assertion weakening, or baseline-only count reductions.

## T060 — Integration Handoff

- Emit a deterministic deleted/renamed path list and expected `_arch_shard_map.py` removals.
- Do not edit the central map. WP07 integrates all cohort handoffs and runs complete architectural route validation.
- Commit owned files and leave worktree clean.

## Definition of Done

- [ ] Every assigned cohort-C file has a terminal verdict.
- [ ] Spent structural scaffolds removed while live governance/security boundaries remain protected.
- [ ] Every cited survivor has nonzero corpus, current authority, and two-sided controlled-fault bite.
- [ ] Focused survivors pass; deleted paths are in deterministic map handoff.
- [ ] No edits outside exact ownership.

## Reviewer Guidance

Sample both deletions and survivors. Reject historical prestige as authority, positive exact shape disguised as architecture, literal-paste probes, empty-corpus gates, and weakening of active security/governance contracts. Confirm assigned-file/ledger coverage is exactly 100%.

## Commit

`git commit -m "test(WP10): sanitize structural cohort c"`
