"""Concurrent code changes, including merge resolutions, invalidate review."""

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.workflow_executor import verify_owned_review_bookkeeping
from specify_cli.workspace.context import resolve_workspace_for_wp
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, OWNED_BRANCH, _file_bytes, _git
from tests.tasks.test_single_branch_owned_review import _review_checkout

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.mark.parametrize("commit_kind", ["linear", "merge"])
def test_owned_review_refuses_concurrent_code_commits_without_reverting_them(tmp_path: Path, commit_kind: str) -> None:
    primary, owned, _ = _review_checkout(tmp_path)
    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    workspace = resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    before = _file_bytes(primary)
    if commit_kind == "merge":
        _git(owned, "checkout", "-b", "concurrent-status")
        with (mission_dir / "status.json").open("a", encoding="utf-8") as status:
            status.write("\n")
        _git(owned, "add", "kitty-specs")
        _git(owned, "commit", "-m", "Other status bookkeeping")
        _git(owned, "checkout", OWNED_BRANCH)
        with (mission_dir / "status.events.jsonl").open("a", encoding="utf-8") as events:
            events.write("\n")
        _git(owned, "add", "kitty-specs")
        _git(owned, "commit", "-m", "First-parent status bookkeeping")
        _git(owned, "merge", "--no-ff", "--no-commit", "concurrent-status")
    (owned / "src" / "feature.py").write_text("VALUE = 99\n", encoding="utf-8")
    _git(owned, "add", "src/feature.py")
    _git(owned, "commit", "-m", "Concurrent code change")
    concurrent_head = _git(owned, "rev-parse", "HEAD")
    if commit_kind == "merge":
        assert "src/feature.py" not in _git(
            owned, "log", "--format=", "--name-only", f"{workspace.implementation_head_commit}..HEAD",
        )

    with pytest.raises(RuntimeError, match="Implementation changed"):
        verify_owned_review_bookkeeping(workspace, mission_dir)

    assert _git(owned, "rev-parse", "HEAD") == concurrent_head
    assert (owned / "src" / "feature.py").read_text(encoding="utf-8") == "VALUE = 99\n"
    assert _file_bytes(primary) == before
