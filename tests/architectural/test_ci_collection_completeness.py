"""Every collected test node remains reachable on a push to the primary branch.

Authority: open CI-integrity epic #1931.  This is the sole retained end-to-end
route oracle; closed-issue filename pins, parser micro-tests, historical
baselines, and scanner-self-defense scaffolds were retired.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural


def test_every_test_node_is_collected_on_a_push_to_main() -> None:
    universe = gc.collect_universe()
    models = gc.load_workflow_models()
    gates = gc.load_gates()
    active = gc.main_push_active_jobs(models)
    report = gc.main_push_uncollected(universe, gates, models)

    assert universe, "test universe is empty"
    assert active, "no modeled CI jobs run on a primary-branch push"
    assert report.orphan_count == 0, (
        f"{report.orphan_count} of {report.total} collected nodes run in no "
        f"primary-push job: {sorted(report.orphan_files)[:30]}"
    )


def test_orphan_sweep_and_parallel_pool_are_disjoint(tmp_path: Path) -> None:
    """GC-2: the serial orphan sweep must not also enter its parallel pool."""
    universe = gc.collect_universe()
    gates = gc.load_gates()
    topology_gates = [
        gate
        for gate in gates
        if gate.workflow == "ci-quality.yml"
        and gate.job in {"fast-tests-sync-orphan-sweep", "unit-contract-residual"}
    ]
    orphan_gate = next(
        gate
        for gate in topology_gates
        if gate.job == "fast-tests-sync-orphan-sweep"
        and gate.marker_expr == "not windows_ci"
    )
    pool_gate = next(
        gate
        for gate in topology_gates
        if gate.job == "unit-contract-residual"
    )
    orphan_path = "tests/sync/test_orphan_sweep.py"
    serial_nodes = gc.cross_job_disjoint_selection(
        [orphan_gate], [orphan_gate], universe
    )

    assert serial_nodes, "the live serial orphan-sweep selection is empty"
    assert not gc.cross_job_disjoint_selection([orphan_gate], [pool_gate], universe)
    assert orphan_path in pool_gate.ignores, "parallel pool lost its live exclusion"

    workflow_path = gc.WORKFLOWS_DIR / "ci-quality.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    pool_step = next(
        step
        for step in workflow["jobs"]["unit-contract-residual"]["steps"]
        if "run" in step and orphan_path in step["run"]
    )
    ignored_flag = f"--ignore={orphan_path}"
    assert pool_step["run"].count(ignored_flag) == 1
    pool_step["run"] = pool_step["run"].replace(ignored_flag, "", 1)
    faulty_workflow = tmp_path / "ci-quality.yml"
    faulty_workflow.write_text(
        yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8"
    )
    pool_without_orphan_ignore = next(
        gate
        for gate in gc.parse_workflow(faulty_workflow)
        if gate.job == "unit-contract-residual"
    )
    fault_overlap = gc.cross_job_disjoint_selection(
        [orphan_gate], [pool_without_orphan_ignore], universe
    )
    assert fault_overlap == serial_nodes, (
        "removing the actual parallel-pool ignore did not double-run the live "
        f"orphan-sweep selection: {sorted(fault_overlap)[:20]}"
    )
