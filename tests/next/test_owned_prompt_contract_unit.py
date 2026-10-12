"""Prompt descriptions distinguish owned, lane and planning workspaces."""

from dataclasses import replace
from pathlib import Path

import pytest

from runtime.next.prompt_builder import _owned_review_commands, _workspace_contract_line
from specify_cli.workspace.context import ResolvedWorkspace

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _workspace() -> ResolvedWorkspace:
    return ResolvedWorkspace(
        mission_slug="test", wp_id="WP01", execution_mode="worktree", mode_source="test",
        resolution_kind="single_branch_workspace", workspace_name="owned", worktree_path=Path("owned"),
        branch_name="codex/test", lane_id=None, lane_wp_ids=[],
        implementation_base_commit="1" * 40, implementation_head_commit="2" * 40,
    )


def test_workspace_description_uses_the_actual_execution_contract() -> None:
    workspace = _workspace()
    assert _workspace_contract_line(workspace, "WP01", True) == "Workspace contract: registered owned checkout"
    assert _workspace_contract_line(workspace, "WP01", False) == "Workspace contract: repository root planning workspace"
    lane = replace(workspace, lane_id="lane-a", lane_wp_ids=["WP01", "WP02"])
    assert _workspace_contract_line(lane, "WP01", False) == "Workspace contract: lane lane-a shared by WP01, WP02"
    assert _workspace_contract_line(replace(lane, lane_wp_ids=[]), "WP01", False).endswith("shared by WP01")


@pytest.mark.parametrize("missing", ["implementation_base_commit", "implementation_head_commit"])
def test_owned_review_without_a_proven_range_has_no_review_commands(missing: str) -> None:
    workspace = replace(_workspace(), **{missing: None})
    with pytest.raises(ValueError, match="proven implementation base and HEAD"):
        _owned_review_commands(workspace)
