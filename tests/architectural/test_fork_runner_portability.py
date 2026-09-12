"""Fork PR workflows must not depend on upstream-only Blacksmith runners."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = REPO_ROOT / ".github" / "workflows"
LINUX_RUNNER = (
    "${{ github.repository == 'Priivacy-ai/spec-kitty' && "
    "'blacksmith-4vcpu-ubuntu-2404' || 'ubuntu-latest' }}"
)
WINDOWS_RUNNER = (
    "${{ github.repository == 'Priivacy-ai/spec-kitty' && "
    "'blacksmith-4vcpu-windows-2025' || 'windows-latest' }}"
)

EXPECTED_RUNNERS = {
    "canonical-producer-lint.yml": {"lint": LINUX_RUNNER},
    "ci-windows.yml": {
        "changes": LINUX_RUNNER,
        "windows-critical": WINDOWS_RUNNER,
    },
    "docs-freshness.yml": {"docs-freshness": LINUX_RUNNER},
    "drift-detector.yml": {"drift-detector": LINUX_RUNNER},
    "plugin-validate.yml": {
        "validate-claude-plugin": LINUX_RUNNER,
        "validate-codex-plugin": LINUX_RUNNER,
    },
    "release-readiness.yml": {
        "check-readiness": LINUX_RUNNER,
        "cutover-guard": LINUX_RUNNER,
    },
    "ui-e2e.yml": {"ui-e2e": LINUX_RUNNER},
}

QUALITY_WORKFLOWS = (
    "ci-quality.yml",
    "module-doctrine-fast.yml",
    "module-doctrine-integration.yml",
    "module-kernel.yml",
    "module-packs.yml",
)


def test_pr_workflows_select_hosted_runners_for_forks() -> None:
    for workflow_name, expected_jobs in EXPECTED_RUNNERS.items():
        workflow = yaml.safe_load(
            (WORKFLOW_ROOT / workflow_name).read_text(encoding="utf-8")
        )
        jobs = workflow["jobs"]

        assert {
            job_name: jobs[job_name]["runs-on"] for job_name in expected_jobs
        } == expected_jobs


def test_quality_workflows_do_not_require_blacksmith_in_forks() -> None:
    for workflow_name in QUALITY_WORKFLOWS:
        workflow = yaml.safe_load(
            (WORKFLOW_ROOT / workflow_name).read_text(encoding="utf-8")
        )

        for job_name, job in workflow["jobs"].items():
            runner = job.get("runs-on")
            if runner is None:
                continue
            assert runner in {LINUX_RUNNER, "ubuntu-latest"}, (
                f"{workflow_name}:{job_name} has a non-portable runner: {runner}"
            )


def test_ci_quality_uses_a_fork_specific_concurrency_namespace() -> None:
    workflow = yaml.safe_load(
        (WORKFLOW_ROOT / "ci-quality.yml").read_text(encoding="utf-8")
    )

    assert workflow["concurrency"]["group"] == (
        "ci-quality-${{ github.repository == 'Priivacy-ai/spec-kitty' && "
        "github.ref || format('fork-{0}', github.ref) }}"
    )
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_ci_windows_supports_an_exact_head_candidate_inventory() -> None:
    """Manual Windows evidence must pin both checkout identity and inventory."""
    workflow = yaml.safe_load(
        (WORKFLOW_ROOT / "ci-windows.yml").read_text(encoding="utf-8")
    )
    workflow_on = workflow.get("on", workflow.get(True))
    inputs = workflow_on["workflow_dispatch"]["inputs"]

    assert inputs["expected_sha"]["required"] is True
    assert inputs["test_paths_json"]["required"] is True
    assert inputs["expected_count"]["required"] is True

    job = workflow["jobs"]["exact-head-candidate"]
    assert job["runs-on"] == WINDOWS_RUNNER
    assert job["if"] == "${{ github.event_name == 'workflow_dispatch' }}"

    checkout = next(
        step for step in job["steps"] if step.get("uses") == "actions/checkout@v6"
    )
    assert checkout["with"]["ref"] == "${{ inputs.expected_sha }}"
    assert checkout["with"]["fetch-depth"] == 0

    transport = next(
        step
        for step in job["steps"]
        if step.get("name") == "Run portable transport lease contract"
    )
    assert transport["run"] == "uv run python scripts/ci/run_selected_tests.py"
    assert transport["env"] == {
        "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        "SPEC_KITTY_TEST_PATHS_JSON": '["tests/sync/test_transport_result_lease.py"]',
        "SPEC_KITTY_EXPECTED_TEST_COUNT": "20",
    }

    runner = next(
        step
        for step in job["steps"]
        if step.get("name") == "Run exact candidate inventory"
    )
    assert runner["run"] == "uv run python scripts/ci/run_selected_tests.py"
    assert runner["env"] == {
        "SPEC_KITTY_TEST_PATHS_JSON": "${{ inputs.test_paths_json }}",
        "SPEC_KITTY_EXPECTED_TEST_COUNT": "${{ inputs.expected_count }}",
    }
