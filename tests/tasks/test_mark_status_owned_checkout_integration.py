"""The completion command from an owned prompt records a real subtask delta."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks
from specify_cli.status import read_events, reduce
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_subtask_completion_preserves_authored_files_and_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    monkeypatch.chdir(owned)
    before = _file_bytes(primary)
    head, index = _git(primary, "rev-parse", "HEAD"), _git(primary, "ls-files", "--stage")
    authored = {p: p.read_bytes() for p in [mission_dir / "tasks.md", *list((mission_dir / "tasks").glob("WP01*.md"))]}

    # Assumption check
    assert "T001" not in reduce(read_events(mission_dir)).work_packages["WP01"].get("subtasks", {})

    # Act
    result = CliRunner().invoke(tasks.app, [
        "mark-status", "T001", "--status", "done", "--mission", MISSION_SLUG, "--owned-checkout", str(owned),
    ])

    # Assert
    assert result.exit_code == 0, result.output
    state = reduce(read_events(mission_dir)).work_packages["WP01"]
    assert state["subtasks"]["T001"] == "done"
    assert {p: p.read_bytes() for p in authored} == authored
    assert _file_bytes(primary) == before
    assert _git(primary, "rev-parse", "HEAD") == head
    assert _git(primary, "ls-files", "--stage") == index
