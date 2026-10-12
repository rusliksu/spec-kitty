"""Scope: record the prerequisite analysis in the owned checkout only."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app
from tests.next.test_owned_implement_next_integration import _add_origin
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_analysis_is_written_and_committed_without_primary_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    (owned / ".gitignore").write_text(".kittify/sync-state.json\n", encoding="utf-8")
    (mission_dir / "spec.md").write_text("# Specification\n\nSynthetic owned implementation.\n", encoding="utf-8")
    (mission_dir / "plan.md").write_text("# Plan\n\nUse the registered checkout.\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add the synthetic planning baseline")
    monkeypatch.chdir(owned)
    before = _file_bytes(primary)
    primary_head = _git(primary, "rev-parse", "HEAD")
    owned_head = _git(owned, "rev-parse", "HEAD")

    # Assumption check
    assert not (mission_dir / "analysis-report.md").exists()
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()

    # Act
    result = CliRunner().invoke(app, [
        "record-analysis", "--mission", MISSION_SLUG, "--owned-checkout", str(owned),
        "--agent", "codex", "--input-file", "-", "--json",
    ], input="---\nschema: analysis-findings/v1\nfindings: []\n---\nSynthetic analysis.\n")

    # Assert
    assert result.exit_code == 0, result.output
    assert (mission_dir / "analysis-report.md").is_file()
    assert _git(owned, "rev-parse", "HEAD") != owned_head
    assert _git(owned, "ls-files", "--error-unmatch", f"kitty-specs/{MISSION_SLUG}/analysis-report.md")
    assert _git(owned, "status", "--porcelain") == ""
    assert _file_bytes(primary) == before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
