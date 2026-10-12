"""A blocked-work note emitted by an owned prompt stays in its checkout."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_history_note_writes_only_the_owned_work_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    monkeypatch.chdir(owned)
    before = _file_bytes(primary)
    head, index = _git(primary, "rev-parse", "HEAD"), _git(primary, "ls-files", "--stage")

    # Assumption check
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()

    # Act
    result = CliRunner().invoke(tasks.app, [
        "add-history", "WP01", "--note", "Blocked: synthetic review dependency",
        "--agent", "codex", "--mission", MISSION_SLUG, "--owned-checkout", str(owned),
    ])

    # Assert
    assert result.exit_code == 0, result.output
    assert "Blocked: synthetic review dependency" in next((mission_dir / "tasks").glob("WP01*.md")).read_text(encoding="utf-8")
    assert _file_bytes(primary) == before
    assert _git(primary, "rev-parse", "HEAD") == head
    assert _git(primary, "ls-files", "--stage") == index
