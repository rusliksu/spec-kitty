"""Unit tests for ``CoordinationWorkspace``.

These cover the FR-024 / FR-018 lifecycle contract:

* :meth:`CoordinationWorkspace.resolve` creates the worktree on first
  call and is idempotent on subsequent calls.
* A mismatched HEAD raises :class:`CoordinationWorkspaceBranchMismatch`
  with the stable ``error_code = "COORDINATION_WORKTREE_BRANCH_MISMATCH"``.
* :meth:`CoordinationWorkspace.teardown` is idempotent (safe to call on
  an absent worktree).
* :meth:`CoordinationWorkspace.is_present` reflects on-disk state.
"""

from __future__ import annotations

import subprocess
import shutil
import multiprocessing
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.coordination import (
    CoordinationWorkspace,
    CoordinationWorkspaceBranchMismatch,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MISSION_SLUG = "demo-feature"
MID8 = "01J6XW9K"
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}-{MID8}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _worktree_list(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        text=True,
    )


@pytest.fixture
def repo_with_coord_branch(tmp_path: Path) -> Path:
    """A tmp git repo with the coordination branch already created.

    Mirrors the post-WP03 state: ``mission create`` created the branch
    but not yet a coordination worktree.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    _git(repo, "branch", COORD_BRANCH)
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worktree_path_is_pure(tmp_path: Path) -> None:
    path = CoordinationWorkspace.worktree_path(tmp_path, MISSION_SLUG, MID8)
    assert path == tmp_path / ".worktrees" / f"{MISSION_SLUG}-{MID8}-coord"
    # Pure: no filesystem effect.
    assert not path.exists()


def test_branch_name_is_pure() -> None:
    assert CoordinationWorkspace.branch_name(MISSION_SLUG, MID8) == COORD_BRANCH


def test_resolve_creates_worktree(repo_with_coord_branch: Path) -> None:
    path = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert path.exists()
    assert path.is_dir()
    # HEAD should be on the coord branch.
    head = subprocess.check_output(
        ["git", "-C", str(path), "symbolic-ref", "HEAD"], text=True,
    ).strip()
    assert head == f"refs/heads/{COORD_BRANCH}"


def test_resolve_reuses_existing(repo_with_coord_branch: Path) -> None:
    first = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    # Touch a file so we can verify the worktree wasn't recreated.
    marker = first / "MARKER"
    marker.write_text("preserved\n")

    second = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert first == second
    assert marker.exists()
    assert marker.read_text() == "preserved\n"


def _resolve_in_process(
    repo: Path, slug: str, ready: Any, entered: Any, release: Any, result: Any,
) -> None:
    """Pause at Git creation without substituting Git's effects."""
    from filelock import FileLock

    original_run = subprocess.run
    original_acquire = FileLock._acquire

    def observed_acquire(lock: Any) -> None:
        original_acquire(lock)
        if release is None and not lock.is_locked:
            ready.set()

    def controlled_run(command: list[str], *args: Any, **kwargs: Any) -> Any:
        if release is None and "worktree" in command and "list" in command:
            entered.set()
            ready.set()
        if "worktree" in command and "add" in command:
            entered.set()
            if release is not None and not release.wait(30):
                raise TimeoutError("Test did not release worktree creation")
        return original_run(command, *args, **kwargs)

    try:
        with (
            patch("specify_cli.coordination.workspace.subprocess.run", controlled_run),
            patch.object(FileLock, "_acquire", observed_acquire),
        ):
            path = CoordinationWorkspace.resolve(repo, slug, MID8)
        result.send(("ok", str(path)))
    except Exception as exc:
        result.send(("error", repr(exc)))
    finally:
        result.close()


def test_different_missions_serialize_shared_git_metadata(repo_with_coord_branch: Path) -> None:
    """A sibling must not scan registrations while Git creates one."""
    # Arrange
    repo = repo_with_coord_branch
    _git(repo, "branch", f"kitty/mission-other-mission-{MID8}")
    linked = repo.parent / "linked"
    _git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    ctx = multiprocessing.get_context("spawn")
    first_ready, second_ready = ctx.Event(), ctx.Event()
    first_entered, second_entered, release = ctx.Event(), ctx.Event(), ctx.Event()
    first_reader, first_writer = ctx.Pipe(duplex=False)
    second_reader, second_writer = ctx.Pipe(duplex=False)
    first = ctx.Process(target=_resolve_in_process, args=(repo, MISSION_SLUG, first_ready, first_entered, release, first_writer))
    second = ctx.Process(target=_resolve_in_process, args=(linked, "other-mission", second_ready, second_entered, None, second_writer))
    # Assumption check
    assert repo != linked
    assert "linked" in _worktree_list(repo)
    try:
        first.start()
        assert first_entered.wait(30), "first process never reached Git creation"
        second.start()
        assert second_ready.wait(30), "second process neither contended nor entered Git"
        # Act: observe actual lock contention while the first creation is paused.
        overlapping_creation = second_entered.is_set()
    finally:
        release.set()
        for process in (first, second):
            if process.pid is not None:
                process.join(40)
                if process.is_alive():
                    process.terminate()
                    process.join(10)
        first_writer.close()
        second_writer.close()
    # Assert
    assert not overlapping_creation, "different processes entered shared Git metadata creation together"
    for process, reader in ((first, first_reader), (second, second_reader)):
        assert process.exitcode == 0
        assert reader.poll(1), "worker returned no result"
        result = reader.recv()
        reader.close()
        assert result[0] == "ok", result
        assert (Path(result[1]) / "seed.txt").read_text() == "seed\n"
    assert second_entered.is_set()


def test_resolve_recovers_stale_prunable_registration(
    repo_with_coord_branch: Path,
) -> None:
    path = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    shutil.rmtree(path)
    assert not path.exists()
    assert "prunable" in _worktree_list(repo_with_coord_branch)

    recovered = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )

    assert recovered == path
    assert recovered.exists()
    assert "prunable" not in _worktree_list(repo_with_coord_branch)


def test_busy_metadata_lock_fails_without_creating_worktree(
    repo_with_coord_branch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from filelock import FileLock
    from specify_cli.coordination import workspace

    # Arrange
    repo = repo_with_coord_branch
    lock_path = repo / ".git" / "spec-kitty-locks" / "coord-worktrees.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(workspace, "_RESOLVE_LOCK_TIMEOUT_SECONDS", 0.05)
    target = repo / ".worktrees" / f"{MISSION_SLUG}-{MID8}-coord"
    # Assumption check
    assert not target.exists()
    # Act / Assert
    with FileLock(str(lock_path)):
        with pytest.raises(TimeoutError, match="coordination worktree metadata"):
            CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)
        assert not target.exists()
    assert CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8) == target


def test_resolve_branch_mismatch_raises(repo_with_coord_branch: Path) -> None:
    path = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    # Switch the worktree to a different branch.
    _git(path, "checkout", "-q", "-b", "interloper")

    with pytest.raises(CoordinationWorkspaceBranchMismatch) as exc:
        CoordinationWorkspace.resolve(
            repo_with_coord_branch, MISSION_SLUG, MID8,
        )

    err = exc.value
    assert err.error_code == "COORDINATION_WORKTREE_BRANCH_MISMATCH"
    assert err.expected_ref == COORD_BRANCH
    assert "interloper" in err.actual_ref
    assert err.worktree_path == path
    _git(path, "checkout", "-q", COORD_BRANCH)
    assert CoordinationWorkspace.resolve(repo_with_coord_branch, MISSION_SLUG, MID8) == path


def test_teardown_idempotent(repo_with_coord_branch: Path) -> None:
    path = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert path.exists()

    CoordinationWorkspace.teardown(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert not path.exists()

    # Second call is a no-op.
    CoordinationWorkspace.teardown(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert not path.exists()


def test_teardown_prunes_stale_missing_registration(
    repo_with_coord_branch: Path,
) -> None:
    path = CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    shutil.rmtree(path)
    assert not path.exists()
    assert "prunable" in _worktree_list(repo_with_coord_branch)

    CoordinationWorkspace.teardown(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )

    worktree_list = _worktree_list(repo_with_coord_branch)
    assert str(path) not in worktree_list
    assert "prunable" not in worktree_list


def test_teardown_does_not_delete_branch(
    repo_with_coord_branch: Path,
) -> None:
    CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    CoordinationWorkspace.teardown(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    # The branch must still exist; deletion is the merge command's job.
    result = subprocess.run(
        ["git", "-C", str(repo_with_coord_branch), "rev-parse",
         "--verify", f"refs/heads/{COORD_BRANCH}"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_is_present(repo_with_coord_branch: Path) -> None:
    assert not CoordinationWorkspace.is_present(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    CoordinationWorkspace.resolve(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert CoordinationWorkspace.is_present(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    CoordinationWorkspace.teardown(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
    assert not CoordinationWorkspace.is_present(
        repo_with_coord_branch, MISSION_SLUG, MID8,
    )
