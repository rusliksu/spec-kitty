"""Acceptance for a command guard that detects primary index-only mutations."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.tasks.test_linked_worktree_planning_context import (
    LinkedMission,
    checked_cli as checked_cli,
    linked_mission as linked_mission,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]

Command = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture
def run_cli() -> Command:
    """Drive the existing guard with a real local command, not a mocked result."""
    def invoke(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, timeout=30)

    return invoke


@pytest.mark.parametrize("exit_code", [0, 7])
def test_primary_index_only_mutation_is_rejected(
    linked_mission: LinkedMission, checked_cli: Command, exit_code: int,
) -> None:
    """A command can change index flags while HEAD, bytes and porcelain stay equal."""
    primary = linked_mission.primary
    index = primary / ".git" / "index"
    before_index = index.read_bytes()
    before_readme = (primary / "README.md").read_bytes()
    program = (
        "import subprocess, sys; "
        "subprocess.run(['git', '-C', sys.argv[1], 'update-index', "
        "'--assume-unchanged', 'README.md'], check=True); sys.exit(int(sys.argv[2]))"
    )
    with pytest.raises(AssertionError, match="primary"):
        checked_cli(linked_mission.linked, sys.executable, "-c", program, str(primary), str(exit_code))

    assert index.read_bytes() != before_index
    assert (primary / "README.md").read_bytes() == before_readme
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=primary, text=True) == ""


@pytest.mark.parametrize("exit_code", [0, 7])
def test_primary_file_mutation_is_rejected(
    linked_mission: LinkedMission, checked_cli: Command, exit_code: int,
) -> None:
    program = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('changed'); sys.exit(int(sys.argv[2]))"
    with pytest.raises(AssertionError, match="primary"):
        checked_cli(linked_mission.linked, sys.executable, "-c", program,
                    str(linked_mission.primary / "README.md"), str(exit_code))
