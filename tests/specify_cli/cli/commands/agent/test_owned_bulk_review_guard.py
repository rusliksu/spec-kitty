"""A proven owned range must not collapse the bulk-review diff to branch..branch."""

import json
from pathlib import Path

import pytest
import typer
from rich.console import Console

from specify_cli.bulk_edit.gate import check_review_diff_compliance, render_diff_check_failure
from specify_cli.cli.commands.agent.workflow import _enforce_bulk_edit_diff_compliance
from specify_cli.workspace.context import resolve_workspace_for_wp
from tests.specify_cli.mission_v1.test_guards_bulk_edit import VALID_OCCURRENCE_MAP
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, OWNED_BRANCH, _file_bytes, _git
from tests.tasks.test_single_branch_owned_review import _review_checkout

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_bulk_review_refuses_a_forbidden_implementation_change(tmp_path: Path) -> None:
    # Arrange
    primary, owned, base = _review_checkout(tmp_path)
    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    meta_path = mission_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["change_mode"] = "bulk_edit"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    (mission_dir / "occurrence_map.yaml").write_text(
        VALID_OCCURRENCE_MAP.replace("code_symbols:\n    action: rename", "code_symbols:\n    action: do_not_change"),
        encoding="utf-8",
    )
    _git(owned, "add", "kitty-specs")
    _git(owned, "commit", "-m", "Declare the forbidden fixture surface")
    workspace = resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    before = _file_bytes(primary)

    # Assumption check
    assert "src/feature.py" in _git(owned, "diff", "--name-only", f"{base}..HEAD")
    assert workspace.branch_name == OWNED_BRANCH

    # Act / Assert
    with pytest.raises(typer.Exit) as refusal:
        _enforce_bulk_edit_diff_compliance(
            feature_dir=mission_dir, main_repo_root=owned, mission_slug=MISSION_SLUG,
            target_branch=OWNED_BRANCH, review_workspace=workspace,
            check_review_diff_compliance=check_review_diff_compliance,
            render_diff_check_failure=render_diff_check_failure, rich_console=Console(),
        )
    assert refusal.value.exit_code == 1
    assert _file_bytes(primary) == before
