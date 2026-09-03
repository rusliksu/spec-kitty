"""Fork PR workflows must not depend on upstream-only Blacksmith runners."""

from __future__ import annotations

from pathlib import Path

import yaml


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
