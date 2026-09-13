"""A single-branch review must inspect real commits against a proven base."""

from pathlib import Path
import json
import shutil

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks
from specify_cli.workspace.context import WorkspaceResolutionError, resolve_workspace_for_wp
from specify_cli.workspace.owned import verify_review_head
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, OWNED_BRANCH, _file_bytes, _git, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _review_checkout(tmp_path: Path, *, implementation: bool = True) -> tuple[Path, Path, str]:
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    remote = tmp_path / "remote.git"
    _git(primary, "clone", "--bare", str(primary), str(remote))
    _git(primary, "remote", "add", "origin", str(remote))
    _git(primary, "fetch", "origin")
    _git(primary, "branch", "--set-upstream-to=origin/main", "main")
    base = _git(primary, "rev-parse", "origin/main")
    (owned / ".gitignore").write_text(".kittify/sync-state.json\n", encoding="utf-8")
    if implementation:
        (owned / "src").mkdir()
        (owned / "src" / "feature.py").write_text("VALUE = 42\n", encoding="utf-8")
        wp = mission_dir / "tasks" / "WP01-owned-seam.md"
        wp.write_text(
            wp.read_text(encoding="utf-8").replace('execution_mode: "code_change"', 'execution_mode: "code_change"\nowned_files: [src/feature.py]'),
            encoding="utf-8",
        )
        _git(owned, "add", ".")
        _git(owned, "commit", "-m", "Implement the owned work package")
    return primary, owned, base


@pytest.mark.parametrize("implementation", [True, False])
def test_single_branch_readiness_requires_implementation_commits(tmp_path: Path, implementation: bool) -> None:
    primary, owned, base = _review_checkout(tmp_path, implementation=implementation)
    before = _file_bytes(primary)
    workspace = resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    assert workspace.resolution_kind == "single_branch_workspace"
    assert workspace.worktree_path == owned
    assert workspace.lane_id is None and workspace.context is None
    assert workspace.implementation_base_commit == base
    assert workspace.implementation_head_commit == _git(owned, "rev-parse", "HEAD")
    ready, guidance = tasks._validate_ready_for_review(owned, MISSION_SLUG, "WP01", False, effective_root=owned)
    assert ready is implementation, guidance
    if not implementation:
        assert "commit" in " ".join(guidance).lower()
    assert _file_bytes(primary) == before


@pytest.mark.parametrize("failure", ["branch", "detached", "no-upstream", "behind-upstream"])
def test_single_branch_refuses_unproven_workspace(tmp_path: Path, failure: str) -> None:
    primary, owned, _ = _review_checkout(tmp_path)
    if failure == "branch":
        _git(owned, "checkout", "-b", "other-work")
    elif failure == "detached":
        _git(owned, "checkout", "--detach")
    elif failure == "no-upstream":
        _git(primary, "config", "--unset", "branch.main.remote")
    else:
        (primary / "new-base.txt").write_text("Upstream advanced\n", encoding="utf-8")
        _git(primary, "add", ".")
        _git(primary, "commit", "-m", "Advance primary upstream")
        _git(primary, "push", "origin", "main")
    before = _file_bytes(primary)
    with pytest.raises(WorkspaceResolutionError):
        resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    assert _file_bytes(primary) == before


def test_review_head_change_is_refused(tmp_path: Path) -> None:
    primary, owned, _ = _review_checkout(tmp_path)
    workspace = resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    assert workspace.implementation_head_commit is not None
    (owned / "src" / "feature.py").write_text("VALUE = 99\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Change code after review evidence")
    with pytest.raises(WorkspaceResolutionError, match="review-head-changed"):
        verify_review_head(owned, OWNED_BRANCH, workspace.implementation_head_commit)


def test_owned_readiness_refuses_missing_wp(tmp_path: Path) -> None:
    primary, owned, _ = _review_checkout(tmp_path)
    ready, guidance = tasks._validate_ready_for_review(primary, MISSION_SLUG, "WP99", False, effective_root=owned)
    assert not ready
    assert "WP99" in " ".join(guidance)


def test_planning_commits_do_not_count_as_implementation(tmp_path: Path) -> None:
    primary, owned, _ = _review_checkout(tmp_path, implementation=False)
    wp = owned / "kitty-specs" / MISSION_SLUG / "tasks" / "WP01-owned-seam.md"
    wp.write_text(
        wp.read_text(encoding="utf-8").replace('execution_mode: "code_change"', 'execution_mode: "code_change"\nowned_files: [src/feature.py]'), encoding="utf-8"
    )
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Document implementation scope")
    ready, guidance = tasks._validate_ready_for_review(primary, MISSION_SLUG, "WP01", False, effective_root=owned)
    assert not ready
    assert "No committed implementation" in " ".join(guidance)


def test_review_gate_uses_owned_baseline_and_real_changed_files(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import tasks_move_task
    from specify_cli.review.baseline import BaselineTestResult
    from tests.specify_cli.cli.commands.agent.test_tasks_move_task_pre_review_baseline_read import _make_state

    primary, owned, base = _review_checkout(tmp_path)
    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    shutil.copytree(mission_dir, primary / "kitty-specs" / MISSION_SLUG)
    for root, failures in ((primary, 7), (owned, 2)):
        baseline = BaselineTestResult(
            wp_id="WP01",
            captured_at="2026-09-13T01:00:00+00:00",
            base_branch="main",
            base_commit=base,
            test_runner="pytest",
            total=10,
            passed=10 - failures,
            failed=failures,
            skipped=0,
        )
        path = root / "kitty-specs" / MISSION_SLUG / "tasks" / "WP01-owned-seam" / "baseline-tests.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(baseline.to_dict()), encoding="utf-8")
    st = _make_state(coord_husk=mission_dir)
    st.repo_root, st.main_repo_root, st.owned_checkout = owned, owned, owned
    st.mission_slug, st.target_branch = MISSION_SLUG, OWNED_BRANCH
    st.wp = tasks.locate_work_package(owned, MISSION_SLUG, "WP01", effective_root=owned)
    st.review_workspace = resolve_workspace_for_wp(primary, MISSION_SLUG, "WP01", effective_root=owned)
    before = _file_bytes(primary)
    baseline = tasks_move_task._mt_resolve_gate_baseline(st)
    assert baseline is not None and baseline.failed == 2
    inputs, _ = tasks_move_task._mt_resolve_transition_gate_inputs(st)
    assert "src/feature.py" in inputs.changed_files
    assert inputs.worktree_path == owned
    assert _file_bytes(primary) == before


@pytest.mark.parametrize("collision", [False, True])
def test_owned_move_task_review_cycle_is_durable_without_primary_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, collision: bool) -> None:
    from specify_cli.status import Lane, WPInnerStateDelta, emit_inner_state_changed

    primary, owned, _ = _review_checkout(tmp_path)
    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    runner = CliRunner()
    monkeypatch.chdir(primary)
    common = ["--mission", MISSION_SLUG, "--owned-checkout", str(owned), "--json"]
    claim = runner.invoke(
        tasks.app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_progress",
            "--agent",
            "fixture-implementer",
            "--assignee",
            "Fixture",
            "--shell-pid",
            "12345",
            "--no-auto-commit",
            *common,
        ],
    )
    assert claim.exit_code == 0, claim.output
    emit_inner_state_changed(
        mission_dir,
        "WP01",
        WPInnerStateDelta(subtasks={"T001": Lane.DONE}),
        actor="fixture-implementer",
        mission_slug=MISSION_SLUG,
        repo_root=owned,
        effective_root=owned,
    )
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Record completed implementation")
    if collision:
        shutil.copytree(mission_dir, primary / "kitty-specs" / MISSION_SLUG)
    before, head, index = _file_bytes(primary), _git(primary, "rev-parse", "HEAD"), _git(primary, "ls-files", "--stage")
    for lane, identity in (
        ("for_review", ["--agent", "fixture-implementer"]),
        ("in_review", ["--reviewer", "fixture-reviewer"]),
        ("approved", ["--reviewer", "fixture-reviewer", "--approval-ref", "test://independent-review"]),
    ):
        result = runner.invoke(tasks.app, ["move-task", "WP01", "--to", lane, "--auto-commit", *identity, *common])
        assert result.exit_code == 0, f"{lane}: {result.output} {result.exception}"
    events = [json.loads(line) for line in (mission_dir / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    approval = next(e for e in reversed(events) if e.get("to_lane") == "approved")
    assert approval["review_result"]["reviewer"] == "fixture-reviewer"
    assert approval["review_result"]["verdict"] == "approved"
    artifacts = list((mission_dir / "tasks").rglob("review-cycle-*.md"))
    assert len(artifacts) == 1
    evidence_ref = artifacts[0].relative_to(owned).as_posix()
    assert "test://independent-review" in _git(owned, "show", f"HEAD:{evidence_ref}")
    assert _file_bytes(primary) == before
    assert _git(primary, "rev-parse", "HEAD") == head
    assert _git(primary, "ls-files", "--stage") == index
