"""Read planning prerequisites from the declared checkout without writes."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app
from specify_cli.status.lifecycle_events import emit_mission_created_local
from tests.next.test_owned_implement_next_integration import _add_origin
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, OWNED_BRANCH, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


@pytest.mark.parametrize("from_primary", [False, True])
@pytest.mark.parametrize("resume_probe", [False, True])
def test_prerequisites_read_the_declared_checkout_without_primary_or_owned_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, from_primary: bool, resume_probe: bool,
) -> None:
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    (mission_dir / "spec.md").write_text(
        "# Specification\n\n## Functional Requirements\n"
        "- **FR-001**: Read prerequisites from the declared checkout.\n"
        "\n## User Scenarios and Testing\n"
        "An operator reads the owned mission without changing either checkout.\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text("# Plan\n\nUse the registered checkout.\n", encoding="utf-8")
    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    emit_mission_created_local(
        mission_dir, mission_slug=MISSION_SLUG, mission_id=meta["mission_id"], mission_number=None,
        mission_type=meta["mission_type"], target_branch=OWNED_BRANCH, friendly_name=meta["friendly_name"],
        purpose_tldr=meta["purpose_tldr"], purpose_context=meta["purpose_context"], created_at=meta["created_at"],
    )
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add planning prerequisites")
    monkeypatch.chdir(primary if from_primary else owned)
    before = {root: _file_bytes(root) for root in (primary, owned)}
    heads = {root: _git(root, "rev-parse", "HEAD") for root in (primary, owned)}
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()

    args = [
        "check-prerequisites", "--mission", MISSION_SLUG, "--owned-checkout", str(owned),
        "--json",
    ]
    args += ["--resume-probe"] if resume_probe else ["--include-tasks", "--paths-only"]
    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert Path(payload["feature_dir"]).resolve() == mission_dir.resolve()
    assert payload["target_branch"] == OWNED_BRANCH
    if resume_probe:
        assert payload["resume_state"] == "found"
        assert payload["spec_committed_and_substantive"] is True
    for root in (primary, owned):
        assert _file_bytes(root) == before[root]
        assert _git(root, "rev-parse", "HEAD") == heads[root]
        assert _git(root, "status", "--porcelain") == ""


def test_declared_prerequisites_require_an_explicit_mission_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, owned, _mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    monkeypatch.chdir(primary)
    before = {root: _file_bytes(root) for root in (primary, owned)}
    result = CliRunner().invoke(app, ["check-prerequisites", "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"
    assert "--mission <slug> is required" in result.stdout
    for root in (primary, owned):
        assert _file_bytes(root) == before[root]
        assert _git(root, "status", "--porcelain") == ""
