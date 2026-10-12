"""Scope: claim and resume a WP in an explicitly owned linked checkout."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow, workflow_executor
from tests.next.test_owned_implement_next_integration import _add_origin
from tests.status.test_status_owned_checkout_seam import (
    MISSION_SLUG,
    _file_bytes,
    _git,
    _init_owned_mission,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_claim_and_resume_leave_the_primary_checkout_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
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
    claimed = runner.invoke(workflow.app, args)
    assert claimed.exit_code == 0, claimed.output
    resumed = runner.invoke(workflow.app, args)

    # Assert
    assert resumed.exit_code == 0, resumed.output
    events = [json.loads(line) for line in (mission_dir / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    transitions = [event["to_lane"] for event in events if "to_lane" in event]
    assert transitions == ["planned", "claimed", "in_progress"]
    assert str(owned) in claimed.output
    assert _file_bytes(primary) == primary_before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _git(primary, "ls-files", "--stage") == primary_index
