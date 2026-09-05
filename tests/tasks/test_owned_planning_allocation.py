"""Real-Git acceptance for allocating from the Mission's planning checkout."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from specify_cli.analysis_report import write_analysis_report
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.tasks.test_linked_worktree_planning_context import (
    LinkedMission,
    _git,
    linked_mission,  # noqa: F401 - shared real-Git pytest fixture
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]
SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
MID = "01M1MFE98JDK0S33WSYBQRPSDF"


@pytest.fixture
def allocation_mission(linked_mission: LinkedMission) -> LinkedMission:
    root = linked_mission.mission_dir
    (root / "tasks" / "WP01-allocation.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Owned allocation\n"
        "execution_mode: code_change\nowned_files:\n- README.md\n"
        "dependencies: []\n---\n\n# Owned allocation\n", encoding="utf-8",
    )
    append_event(root, StatusEvent(
        event_id="01M1MFE98JDK0S33WSYBQRPSDG", mission_slug=SLUG, wp_id="WP01",
        from_lane=Lane.PLANNED, to_lane=Lane.PLANNED, at="2026-09-05T00:00:00+00:00",
        actor="fixture", force=False, execution_mode="worktree", mission_id=MID,
    ))
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "planning base")
    write_lanes_json(root, LanesManifest(
        version=1, mission_slug=SLUG, mission_id=MID, mission_branch="codex/task",
        target_branch="codex/task",
        lanes=[ExecutionLane("lane-a", ("WP01",), ("README.md",), (), (), 0)],
        computed_at="2026-09-05T00:00:00+00:00", computed_from="dependency_graph+ownership",
        planning_commit_sha=_git(linked_mission.linked, "rev-parse", "HEAD"),
    ))
    write_analysis_report(
        feature_dir=root, repo_root=linked_mission.linked,
        body="---\nschema: analysis-findings/v1\nfindings: []\n"
             "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n---\n# Analysis\n",
    )
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "finalize allocation fixture")
    return linked_mission


@pytest.mark.parametrize("selector", [SLUG, MID])
def test_owned_planning_command_allocates_and_resumes(
    allocation_mission: LinkedMission,
    run_cli: Callable[..., subprocess.CompletedProcess[str]],
    selector: str,
) -> None:
    ctx = allocation_mission
    primary_index = _git(ctx.primary, "ls-files", "--stage")
    primary_readme = (ctx.primary / "README.md").read_bytes()
    planning_sha = _git(ctx.linked, "rev-parse", "HEAD")
    lane = ctx.primary / ".worktrees" / f"{SLUG}-lane-a"
    for _attempt in range(2):
        result = run_cli(ctx.linked, "agent", "action", "implement", "WP01",
                         "--mission", selector, "--agent", "codex")
        assert result.returncode == 0, result.stdout + result.stderr
        assert lane.is_dir()
        assert _git(lane, "branch", "--show-current") == f"kitty/mission-{SLUG}-lane-a"
        _git(lane, "merge-base", "--is-ancestor", planning_sha, "HEAD")
        assert _git(ctx.primary, "rev-parse", "HEAD") == ctx.primary_head
        assert _git(ctx.primary, "ls-files", "--stage") == primary_index
        assert (ctx.primary / "README.md").read_bytes() == primary_readme
        assert not (ctx.primary / "kitty-specs" / SLUG).exists()
    events = [json.loads(row) for row in (ctx.mission_dir / "status.events.jsonl").read_text().splitlines()]
    assert sum(row.get("to_lane") == "claimed" for row in events) == 1
    assert any(row.get("to_lane") == "in_progress" for row in events)
