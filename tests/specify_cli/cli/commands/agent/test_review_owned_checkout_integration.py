"""An owned review and its rejected rework stay in the registered checkout."""

from pathlib import Path
import re

import pytest
from typer.testing import CliRunner

from runtime.next._tmp_namespace import prompt_tmp_dir
from runtime.next.prompt_builder import build_prompt
from specify_cli.cli.commands.agent import tasks, workflow, workflow_executor
from specify_cli.status import Lane, WPInnerStateDelta, emit_inner_state_changed
from specify_cli.review.lock import ReviewLock
from tests.specify_cli.cli.commands.agent.test_implement_owned_checkout_integration import _implementation_baseline
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _file_bytes, _git
from tests.tasks.test_single_branch_owned_review import _review_checkout

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_review_and_rejected_fix_keep_the_primary_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, base = _review_checkout(tmp_path)
    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    _implementation_baseline(owned, mission_dir)
    monkeypatch.chdir(owned)
    monkeypatch.setattr(workflow_executor, "implement_capture_baseline", lambda **kwargs: None)
    monkeypatch.setattr(workflow_executor, "_implement_trigger_dossier_sync", lambda *args, **kwargs: None)
    runner = CliRunner()
    common = ["--mission", MISSION_SLUG, "--owned-checkout", str(owned)]
    claim = runner.invoke(workflow.app, ["implement", "WP01", "--agent", "codex", *common])
    assert claim.exit_code == 0, claim.output
    (owned / "src" / "feature.py").write_text("VALUE = 43\n", encoding="utf-8")
    _git(owned, "add", "src/feature.py")
    _git(owned, "commit", "-m", "Implement the synthetic WP")
    emit_inner_state_changed(
        mission_dir, "WP01", WPInnerStateDelta(subtasks={"T001": Lane.DONE}),
        actor="codex", mission_slug=MISSION_SLUG, repo_root=owned, effective_root=owned,
    )
    _git(owned, "add", "kitty-specs")
    _git(owned, "commit", "-m", "Record completed fixture subtask")
    ready = runner.invoke(tasks.app, ["move-task", "WP01", "--to", "for_review", "--agent", "codex", "--auto-commit", *common])
    assert ready.exit_code == 0, ready.output
    # Commit the command's remaining liveness annotation before the next claim.
    _git(owned, "add", "kitty-specs")
    _git(owned, "commit", "-m", "Record fixture handoff bookkeeping")
    assert _git(owned, "status", "--porcelain") == "", ready.output
    before = _file_bytes(primary)
    head, index = _git(primary, "rev-parse", "HEAD"), _git(primary, "ls-files", "--stage")

    # Assumption check
    assert "VALUE = 43" in _git(owned, "diff", f"{base}..HEAD", "--", "src/feature.py")
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()
    reviewed_head = _git(owned, "rev-parse", "HEAD")

    next_prompt, _ = build_prompt(
        "review", mission_dir, MISSION_SLUG, "WP01", "claude", primary,
        "software-dev", effective_root=owned,
    )
    assert f"git diff {base}..{reviewed_head} --stat" in next_prompt
    assert "repository root planning workspace" not in next_prompt

    # Act
    review = runner.invoke(workflow.app, ["review", "--agent", "claude", *common])

    # Assert
    assert review.exit_code == 0, review.output
    prompt_match = re.search(r"^\s*cat (.+)$", review.output, re.MULTILINE)
    assert prompt_match is not None
    review_prompt = Path(prompt_match.group(1).strip()).read_text(encoding="utf-8")
    assert base in review_prompt
    assert reviewed_head in review_prompt
    assert "src/feature.py" in review_prompt
    completion = [line for line in (review_prompt + review.output).splitlines() if "spec-kitty agent tasks move-task" in line]
    assert completion and all("--owned-checkout" in line and str(owned) in line for line in completion)
    # CliRunner keeps one process; release simulates the first CLI exiting.
    ReviewLock.release(owned)
    resumed = runner.invoke(workflow.app, ["review", "WP01", "--agent", "claude", *common])
    assert resumed.exit_code == 0, resumed.output
    feedback = tmp_path / "feedback.md"
    feedback.write_text("Use VALUE = 44 for the synthetic fixture.\n", encoding="utf-8")
    rejected = runner.invoke(tasks.app, [
        "move-task", "WP01", "--to", "planned", "--reviewer", "claude",
        "--review-feedback-file", str(feedback), "--auto-commit", *common,
    ])
    assert rejected.exit_code == 0, rejected.output
    _git(owned, "add", "kitty-specs")
    _git(owned, "commit", "-m", "Record fixture rework bookkeeping")
    fix = runner.invoke(workflow.app, ["implement", "WP01", "--agent", "codex", *common])
    assert fix.exit_code == 0, fix.output
    fix_prompt = (prompt_tmp_dir(owned) / f"spec-kitty-implement-{MISSION_SLUG}-WP01.md").read_text(encoding="utf-8")
    assert "# Fix Mode" in fix_prompt
    assert "VALUE = 44" in fix_prompt
    assert "--owned-checkout" in fix_prompt and str(owned) in fix_prompt
    assert _file_bytes(primary) == before
    assert _git(primary, "rev-parse", "HEAD") == head
    assert _git(primary, "ls-files", "--stage") == index
