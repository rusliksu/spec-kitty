"""Scope: claim and resume a WP in an explicitly owned linked checkout."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow, workflow_executor
from specify_cli.analysis_report import write_analysis_report
from tests.next.test_owned_implement_next_integration import _add_origin
from tests.status.test_status_owned_checkout_seam import (
    MISSION_SLUG,
    _file_bytes,
    _git,
    _init_owned_mission,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def _implementation_baseline(owned: Path, mission_dir: Path) -> None:
    (mission_dir / "spec.md").write_text("# Specification\n\nSynthetic owned implementation.\n", encoding="utf-8")
    (mission_dir / "plan.md").write_text("# Plan\n\nImplement the synthetic WP in its owned checkout.\n", encoding="utf-8")
    write_analysis_report(
        feature_dir=mission_dir, repo_root=owned, analyzer_agent="codex",
        body="---\nschema: analysis-findings/v1\nfindings: []\n---\nSynthetic fixture has no analysis findings.\n",
    )
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Record the synthetic implementation baseline")


@pytest.mark.parametrize("auto_pick", [False, True])
def test_owned_claim_and_resume_leave_the_primary_checkout_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, auto_pick: bool,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    _implementation_baseline(owned, mission_dir)
    monkeypatch.chdir(owned)
    # The synthetic consumer has no baseline test runner or hosted dossier.
    monkeypatch.setattr(workflow_executor, "implement_capture_baseline", lambda **kwargs: None)
    monkeypatch.setattr(workflow_executor, "_implement_trigger_dossier_sync", lambda *args, **kwargs: None)
    primary_before = _file_bytes(primary)
    primary_head = _git(primary, "rev-parse", "HEAD")
    primary_index = _git(primary, "ls-files", "--stage")
    args = ["implement", "WP01", "--agent", "codex", "--mission", MISSION_SLUG,
            "--owned-checkout", str(owned)]

    # Assumption check
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()
    assert _git(owned, "status", "--porcelain") == ""

    # Act
    runner = CliRunner()
    claimed = runner.invoke(workflow.app, [item for item in args if item != "WP01"] if auto_pick else args)
    assert claimed.exit_code == 0, claimed.output
    resumed = runner.invoke(workflow.app, args)

    # Assert
    assert resumed.exit_code == 0, resumed.output
    events = [json.loads(line) for line in (mission_dir / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    transitions = [event["to_lane"] for event in events if "to_lane" in event]
    assert transitions == ["planned", "claimed", "in_progress"]
    assert str(owned) in claimed.output
    from runtime.next._tmp_namespace import prompt_tmp_dir

    prompt = (prompt_tmp_dir(owned) / f"spec-kitty-implement-{MISSION_SLUG}-WP01.md").read_text(encoding="utf-8")
    completion_commands = [line for line in (prompt + claimed.output).splitlines() if "spec-kitty agent tasks" in line]
    assert completion_commands
    assert all("--owned-checkout" in line and str(owned) in line for line in completion_commands)
    assert _file_bytes(primary) == primary_before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _git(primary, "ls-files", "--stage") == primary_index


@pytest.mark.parametrize("working_version", ["different", "head"])
def test_owned_claim_refuses_dirty_planning_without_consuming_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, working_version: str,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    _implementation_baseline(owned, mission_dir)
    monkeypatch.chdir(owned)
    wp_file = next((mission_dir / "tasks").glob("WP01*.md"))
    original = wp_file.read_text(encoding="utf-8")
    wp_file.write_text(original + "\nUnowned staged edit.\n", encoding="utf-8")
    _git(owned, "add", str(wp_file))
    wp_file.write_text(original if working_version == "head" else original + "\nUnowned unstaged edit.\n", encoding="utf-8")
    before = (_file_bytes(primary), _file_bytes(owned))
    heads = (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD"))
    index = _git(owned, "ls-files", "--stage")

    # Assumption check
    assert _git(owned, "diff", "--cached", "--name-only")
    assert _git(owned, "diff", "--name-only")

    # Act
    result = CliRunner().invoke(workflow.app, [
        "implement", "WP01", "--agent", "codex", "--mission", MISSION_SLUG,
        "--owned-checkout", str(owned),
    ])

    # Assert
    assert result.exit_code == 1, result.output
    assert "uncommitted planning" in result.output.lower()
    assert (_file_bytes(primary), _file_bytes(owned)) == before
    assert (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD")) == heads
    assert _git(owned, "ls-files", "--stage") == index


def test_owned_claim_commit_failure_restores_status_and_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    _implementation_baseline(owned, mission_dir)
    monkeypatch.chdir(owned)
    hook_dir = tmp_path / "rejecting-hooks"
    hook_dir.mkdir()
    (hook_dir / "pre-commit").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    _git(owned, "config", "core.hooksPath", str(hook_dir))
    unrelated = owned / "unrelated.txt"
    unrelated.write_text("Staged unrelated work.\n", encoding="utf-8")
    _git(owned, "add", "unrelated.txt")
    unrelated.write_text("Unstaged unrelated work.\n", encoding="utf-8")
    before = (_file_bytes(primary), _file_bytes(owned))
    heads = (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD"))
    index = _git(owned, "ls-files", "--stage")
    staged_patch = _git(owned, "diff", "--cached")

    # Assumption check
    assert staged_patch and _git(owned, "diff")

    # Act
    result = CliRunner().invoke(workflow.app, [
        "implement", "WP01", "--agent", "codex", "--mission", MISSION_SLUG,
        "--owned-checkout", str(owned),
    ])

    # Assert
    assert result.exit_code == 1, result.output
    assert "commit" in result.output.lower()
    assert (_file_bytes(primary), _file_bytes(owned)) == before
    assert (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD")) == heads
    assert _git(owned, "ls-files", "--stage") == index
    assert _git(owned, "diff", "--cached") == staged_patch


@pytest.mark.parametrize("refusal", ["foreign_checkout", "missing_mission"])
def test_owned_refusal_writes_neither_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, refusal: str,
) -> None:
    # Arrange
    primary, owned, _ = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    monkeypatch.chdir(owned)
    declared = owned
    mission = MISSION_SLUG
    if refusal == "foreign_checkout":
        declared = tmp_path / "foreign"
        declared.mkdir()
    else:
        mission = "missing-mission"
    before = (_file_bytes(primary), _file_bytes(owned))
    heads = (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD"))

    # Assumption check
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()

    # Act
    result = CliRunner().invoke(workflow.app, [
        "implement", "WP01", "--agent", "codex", "--mission", mission,
        "--owned-checkout", str(declared),
    ])

    # Assert
    assert result.exit_code == 1, result.output
    assert (_file_bytes(primary), _file_bytes(owned)) == before
    assert (_git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD")) == heads
