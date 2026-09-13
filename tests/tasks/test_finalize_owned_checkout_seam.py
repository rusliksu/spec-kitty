"""Finalize must seed the owned WP roster, without bootstrapping a sibling copy."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.mark.parametrize("collision", [False, True])
@pytest.mark.parametrize("dry_run", [False, True])
def test_finalize_seeds_only_the_owned_roster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, collision: bool, dry_run: bool) -> None:
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    (mission_dir / "tasks" / "WP02-new.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Second work package\ndependencies: [WP01]\nsubtasks: [T002]\n---\n# WP02\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Tasks\n\n## Work Package WP01: First\n\n**Dependencies**: None\n\n## Work Package WP02: Second\n\n**Dependencies**: WP01\n",
        encoding="utf-8",
    )
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add a WP requiring canonical bootstrap")
    if collision:
        shutil.copytree(mission_dir, primary / "kitty-specs" / MISSION_SLUG)
        _git(primary, "add", ".")
        _git(primary, "commit", "-m", "Independent primary copy")
    monkeypatch.chdir(primary)
    primary_before, owned_before = _file_bytes(primary), _file_bytes(owned)
    primary_head, primary_index = _git(primary, "rev-parse", "HEAD"), _git(primary, "ls-files", "--stage")
    args = ["finalize-tasks", "--mission", MISSION_SLUG, "--owned-checkout", str(owned), "--json"]
    if dry_run:
        args.append("--validate-only")
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["bootstrap"]["total_wps"] == 2
    assert payload["bootstrap"]["newly_seeded"] == 1
    assert _file_bytes(primary) == primary_before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _git(primary, "ls-files", "--stage") == primary_index
    if dry_run:
        assert _file_bytes(owned) == owned_before
    else:
        snapshot = json.loads((mission_dir / "status.json").read_text(encoding="utf-8"))
        assert snapshot["work_packages"]["WP02"]["lane"] == "planned"
        events = [json.loads(line) for line in (mission_dir / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert sum(event.get("wp_id") == "WP02" and event.get("to_lane") == "planned" for event in events) == 1
