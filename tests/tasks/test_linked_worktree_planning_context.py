"""Planning commands preserve a caller-owned linked-worktree mission root."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
_MISSION_ID = "01M1MFE98JDK0S33WSYBQRPSDF"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _linked_mission(tmp_path: Path) -> tuple[Path, Path]:
    primary = tmp_path / "repo"
    primary.mkdir()
    _git(primary, "init", "-q", "-b", "main")
    _git(primary, "config", "user.email", "test@example.invalid")
    _git(primary, "config", "user.name", "Test")
    (primary / "README.md").write_text("seed\n", encoding="utf-8")
    _git(primary, "add", "README.md")
    _git(primary, "commit", "-q", "-m", "init")

    linked = tmp_path / "linked"
    _git(primary, "worktree", "add", "-q", "-b", "codex/task", str(linked), "main")
    feature_dir = linked / "kitty-specs" / _SLUG
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _SLUG,
                "slug": _SLUG,
                "target_branch": "codex/task",
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        "# Spec\n## Functional Requirements\n"
        "| ID | Requirement | Acceptance | Status |\n| - | - | - | - |\n"
        "| FR-001 | Resolve linked Mission | Command succeeds | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n## WP01\n**Requirement Refs**: FR-001\n",
        encoding="utf-8",
    )
    return primary, feature_dir


def _payload(stdout: str) -> dict[str, object]:
    rows = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    assert rows, stdout
    return json.loads(rows[-1])


def test_check_prerequisites_reads_mission_from_caller_owned_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary, feature_dir = _linked_mission(tmp_path)
    monkeypatch.chdir(feature_dir.parent.parent)

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=primary),
        patch("specify_cli.cli.commands.agent.mission._enforce_git_preflight"),
    ):
        result = CliRunner().invoke(
            app,
            ["check-prerequisites", "--mission", _SLUG, "--paths-only", "--json"],
        )

    assert result.exit_code == 0, result.stdout
    assert _payload(result.stdout)["feature_dir"] == str(feature_dir)
