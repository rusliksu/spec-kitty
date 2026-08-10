"""Every collected test node remains reachable on a push to the primary branch.

Authority: open CI-integrity epic #1931.  This is the sole retained end-to-end
route oracle; closed-issue filename pins, parser micro-tests, historical
baselines, and scanner-self-defense scaffolds were retired.
"""

from __future__ import annotations

import pytest

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
