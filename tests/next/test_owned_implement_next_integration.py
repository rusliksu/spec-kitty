"""Scope: issue an implementation prompt from a registered owned checkout."""

from pathlib import Path

import pytest

from runtime.next.decision import DecisionKind
from runtime.next._internal_runtime import next_step
from runtime.next.runtime_bridge import decide_next_via_runtime, get_or_start_run
from tests.status.test_status_owned_checkout_seam import (
    MISSION_SLUG,
    _file_bytes,
    _git,
    _init_owned_mission,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _add_origin(primary: Path, tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "--bare", str(primary), str(origin))
    _git(primary, "remote", "add", "origin", str(origin))
    _git(primary, "fetch", "origin")
    _git(primary, "branch", "--set-upstream-to", "origin/main", "main")


def test_next_issues_the_owned_work_package_without_writing_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    monkeypatch.chdir(owned)
    primary_before = _file_bytes(primary)
    primary_head = _git(primary, "rev-parse", "HEAD")
    primary_index = _git(primary, "ls-files", "--stage")
    run = get_or_start_run(MISSION_SLUG, owned, "software-dev")
    for _ in range(6):
        issued = next_step(run, agent_id="codex", result="success")
        if issued.step_id == "implement":
            break

    # Assumption check
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()
    assert (mission_dir / "tasks" / "WP01-owned-seam.md").is_file()
    assert issued.step_id == "implement"

    # Act
    decision = decide_next_via_runtime(
        "codex", MISSION_SLUG, "success", owned, effective_root=owned,
    )

    # Assert
    assert decision.kind == DecisionKind.step, decision.reason
    assert decision.wp_id == "WP01"
    assert Path(decision.workspace_path) == owned
    prompt = Path(decision.prompt_file).read_text(encoding="utf-8")
    assert "Owned status seam fixture" in prompt
    assert "--owned-checkout" in prompt
    assert str(owned) in prompt
    assert _file_bytes(primary) == primary_before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _git(primary, "ls-files", "--stage") == primary_index
