"""Real-Git acceptance for allocating from the Mission's planning checkout."""

from __future__ import annotations

import json
import shutil
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
    linked_mission as linked_mission,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]
SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
MID = "01M1MFE98JDK0S33WSYBQRPSDF"


@pytest.fixture
def allocation_mission(linked_mission: LinkedMission) -> LinkedMission:
    root = linked_mission.mission_dir
    _git(linked_mission.primary, "config", "core.longpaths", "true")
    metadata = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    metadata.update(created_at="2026-09-05T00:00:00+00:00", friendly_name="Owned allocation", topology="single_branch")
    (root / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")
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
        version=1, mission_slug=SLUG, mission_id=MID, mission_branch=f"kitty/mission-{SLUG}",
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
    for attempt in range(2):
        caller = ctx.linked if attempt == 0 else ctx.mission_dir / "tasks"
        result = run_cli(caller, "agent", "action", "implement", "WP01",
                         "--mission", selector, "--agent", "codex")
        assert result.returncode == 0, result.stdout + result.stderr
        assert lane.is_dir()
        assert _git(lane, "branch", "--show-current") == f"kitty/mission-{SLUG}-lane-a"
        _git(lane, "merge-base", "--is-ancestor", planning_sha, "HEAD")
        assert _git(ctx.primary, "rev-parse", "HEAD") == ctx.primary_head
        assert _git(ctx.primary, "ls-files", "--stage") == primary_index
        assert (ctx.primary / "README.md").read_bytes() == primary_readme
        assert not (ctx.primary / "kitty-specs" / SLUG).exists()
        registry_path = ctx.primary / ".kittify" / "workspaces" / f"{SLUG}-lane-a.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert registry["current_wp"] == "WP01"
        assert registry["base_branch"] == f"kitty/mission-{SLUG}"
        assert registry["worktree_path"].replace("\\", "/") == f".worktrees/{SLUG}-lane-a"
        assert not (ctx.linked / ".kittify" / "workspaces").exists()
        if attempt == 0:
            (lane / "README.md").write_text("in-progress implementation\n", encoding="utf-8")
        else:
            assert (lane / "README.md").read_text(encoding="utf-8") == "in-progress implementation\n"
    events = [json.loads(row) for row in (ctx.mission_dir / "status.events.jsonl").read_text().splitlines()]
    assert sum(row.get("to_lane") == "claimed" for row in events) == 1
    assert any(row.get("to_lane") == "in_progress" for row in events)


@pytest.mark.parametrize("damage", [
    "dirty", "foreign_branch", "corrupt_lanes", "missing_lanes", "husk", "identity_conflict", "unregistered",
])
def test_invalid_planning_allocation_has_no_side_effects(
    allocation_mission: LinkedMission,
    run_cli: Callable[..., subprocess.CompletedProcess[str]],
    damage: str,
) -> None:
    ctx = allocation_mission
    lane = ctx.primary / ".worktrees" / f"{SLUG}-lane-a"
    caller = ctx.linked
    if damage == "dirty":
        (ctx.linked / "README.md").write_text("uncommitted user work\n", encoding="utf-8")
    elif damage == "foreign_branch":
        _git(ctx.linked, "switch", "-c", "codex/foreign")
    elif damage == "corrupt_lanes":
        (ctx.mission_dir / "lanes.json").write_text("{broken", encoding="utf-8")
        _git(ctx.linked, "add", ".")
        _git(ctx.linked, "commit", "-q", "-m", "corrupt fixture manifest")
    elif damage == "missing_lanes":
        (ctx.mission_dir / "lanes.json").unlink()
        _git(ctx.linked, "add", ".")
        _git(ctx.linked, "commit", "-q", "-m", "remove fixture manifest")
    elif damage == "husk":
        lane.mkdir(parents=True)
        (lane / "user-file").write_text("preserve\n", encoding="utf-8")
    elif damage == "identity_conflict":
        conflicting = ctx.primary / "kitty-specs" / SLUG
        conflicting.mkdir(parents=True)
        metadata = json.loads((ctx.mission_dir / "meta.json").read_text(encoding="utf-8"))
        metadata["mission_id"] = "01M1MFE98JDK0S33WSYBQRPSDX"
        (conflicting / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    else:
        caller = ctx.linked.parent / "unregistered"
        shutil.copytree(ctx.linked, caller)

    def snapshot(root: Path) -> dict[str, bytes]:
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
                if p.is_file() and ".git" not in p.relative_to(root).parts}

    primary_before = snapshot(ctx.primary)
    status_before = (ctx.mission_dir / "status.events.jsonl").read_bytes()
    refs_before = _git(ctx.primary, "show-ref")
    result = run_cli(caller, "agent", "action", "implement", "WP01",
                     "--mission", SLUG, "--agent", "codex")
    assert result.returncode != 0, result.stdout + result.stderr
    expected = {
        "dirty": "OWNED_PLANNING_CHECKOUT_DIRTY",
        "foreign_branch": "OWNED_PLANNING_BRANCH_MISMATCH",
        "corrupt_lanes": "corrupt or malformed",
        "missing_lanes": "lanes.json",
        "husk": "husk",
        "identity_conflict": "different identities",
        "unregistered": "OWNED_PLANNING_CHECKOUT_REQUIRED",
    }
    assert expected[damage] in result.stdout + result.stderr
    assert _git(ctx.primary, "show-ref") == refs_before
    assert snapshot(ctx.primary) == primary_before
    assert (ctx.mission_dir / "status.events.jsonl").read_bytes() == status_before
    assert not (lane / ".git").exists()
