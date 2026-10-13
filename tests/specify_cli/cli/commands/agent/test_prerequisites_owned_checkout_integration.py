"""Read planning prerequisites from the declared checkout without writes."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app
from tests.next.test_owned_implement_next_integration import _add_origin
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, OWNED_BRANCH, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


@pytest.mark.parametrize("from_primary", [False, True])
def test_prerequisites_read_the_declared_checkout_without_primary_or_owned_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, from_primary: bool,
) -> None:
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    (mission_dir / "spec.md").write_text("# Specification\n\nSynthetic owned mission.\n", encoding="utf-8")
    (mission_dir / "plan.md").write_text("# Plan\n\nUse the registered checkout.\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add planning prerequisites")
    monkeypatch.chdir(primary if from_primary else owned)
    before = {root: _file_bytes(root) for root in (primary, owned)}
    heads = {root: _git(root, "rev-parse", "HEAD") for root in (primary, owned)}
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()

    result = CliRunner().invoke(app, [
        "check-prerequisites", "--mission", MISSION_SLUG, "--owned-checkout", str(owned),
        "--include-tasks", "--paths-only", "--json",
    ])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert Path(payload["feature_dir"]).resolve() == mission_dir.resolve()
    assert payload["target_branch"] == OWNED_BRANCH
    for root in (primary, owned):
        assert _file_bytes(root) == before[root]
        assert _git(root, "rev-parse", "HEAD") == heads[root]
        assert _git(root, "status", "--porcelain") == ""
