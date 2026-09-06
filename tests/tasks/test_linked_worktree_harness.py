"""Independent behavioral acceptance for the real-Git linked-Mission harness."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.tasks.linked_worktree_harness import (
    LinkedMission,
    create_linked_mission,
    git,
    snapshot_primary,
    write_mission,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]

Command = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture
def linked_mission(tmp_path: Path) -> LinkedMission:
    return create_linked_mission(tmp_path)


@pytest.fixture
def checked_cli(linked_mission: LinkedMission) -> Command:
    return linked_mission.run


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


def test_registered_topology_and_substantive_mission(linked_mission: LinkedMission) -> None:
    ctx = linked_mission
    registrations = git(ctx.primary, "worktree", "list", "--porcelain").replace("\\", "/")
    assert f"worktree {ctx.linked.as_posix()}\n" in registrations
    assert git(ctx.linked, "branch", "--show-current") == "codex/task"
    assert git(ctx.primary, "branch", "--show-current") == "main"
    assert (ctx.linked / ".git").is_file()
    assert not (ctx.primary / "kitty-specs" / ctx.mission_dir.name).exists()
    metadata = json.loads((ctx.mission_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["mission_id"] == "01M1MFE98JDK0S33WSYBQRPSDF"
    assert metadata["mission_slug"] == "linked-worktree-prerequisite-resolution-01M1MFE9"
    for name in ("spec.md", "plan.md", "tasks.md", "status.events.jsonl", "tasks/WP01.md"):
        assert (ctx.mission_dir / name).stat().st_size > 0
    assert git(ctx.linked, "status", "--porcelain") == ""
    assert git(ctx.primary, "status", "--porcelain") == ""


@pytest.mark.parametrize("exit_code", [0, 7])
def test_command_preserves_cwd_arguments_and_both_output_streams(
    linked_mission: LinkedMission, checked_cli: Command, exit_code: int,
) -> None:
    nested = linked_mission.linked / "nested"
    nested.mkdir()
    program = (
        "import json, os, sys; print(json.dumps([os.getcwd(), sys.argv[1:]])); "
        "print('diagnostic', file=sys.stderr); sys.exit(int(sys.argv[1]))"
    )
    result = checked_cli(nested, sys.executable, "-c", program, str(exit_code), "two words", "--literal")
    assert result.returncode == exit_code
    assert json.loads(result.stdout) == [str(nested), [str(exit_code), "two words", "--literal"]]
    assert result.stderr == "diagnostic\n"


def test_linked_changes_do_not_count_as_primary_mutation(linked_mission: LinkedMission, checked_cli: Command) -> None:
    before = snapshot_primary(linked_mission.primary)
    result = checked_cli(linked_mission.linked, sys.executable, "-c",
                         "from pathlib import Path; Path('local.txt').write_text('linked edit')")
    assert result.returncode == 0
    assert (linked_mission.linked / "local.txt").read_text() == "linked edit"
    assert snapshot_primary(linked_mission.primary) == before


@pytest.mark.parametrize("name", ["untracked.txt", ".kittify/sync-state.json"])
def test_untracked_and_ignored_primary_bytes_are_guarded(
    linked_mission: LinkedMission, checked_cli: Command, name: str,
) -> None:
    path = linked_mission.primary / name
    path.write_text("old", encoding="utf-8")
    with pytest.raises(AssertionError, match="primary"):
        checked_cli(linked_mission.linked, sys.executable, "-c",
                    "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('new')", str(path))


def test_primary_commit_is_rejected(linked_mission: LinkedMission, checked_cli: Command) -> None:
    with pytest.raises(AssertionError, match="primary"):
        checked_cli(linked_mission.primary, "git", "commit", "--allow-empty", "-m", "unexpected primary commit")


def test_failed_command_launch_is_not_swallowed(linked_mission: LinkedMission, checked_cli: Command) -> None:
    before = snapshot_primary(linked_mission.primary)
    with pytest.raises(FileNotFoundError):
        checked_cli(linked_mission.linked, str(linked_mission.linked / "missing-command"))
    assert snapshot_primary(linked_mission.primary) == before


@pytest.mark.parametrize("selector", ["linked-worktree-prerequisite-resolution-01M1MFE9", "01M1MFE98JDK0S33WSYBQRPSDF"])
def test_real_cli_context_resolves_fixture_identity(
    linked_mission: LinkedMission, selector: str, isolated_env: dict[str, str],
) -> None:
    from tests.test_isolation_helpers import get_venv_python

    result = linked_mission.run(
        linked_mission.linked, str(get_venv_python()), "-m", "specify_cli.__init__",
        "agent", "context", "resolve", "--mission", selector, "--action", "plan", "--json",
        env=isolated_env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["feature_dir"] == str(linked_mission.mission_dir)
    assert payload["mission_slug"] == "linked-worktree-prerequisite-resolution-01M1MFE9"
    assert payload["target_branch"] == "codex/task"


@pytest.mark.parametrize("scenario", ["missing", "omitted", "ambiguous", "unsafe", "conflicting"])
def test_negative_selector_inputs_have_real_distinct_identities(linked_mission: LinkedMission, scenario: str) -> None:
    """Validate fixture inputs only; WP02/WP03 own the consumer refusal assertions."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.missions.operation_context import MissionSurfaceConflictError, resolve_mission_operation_context

    ctx = linked_mission
    selector: str | None = "linked-worktree-prerequisite-resolution-01M1MFE9"
    if scenario in ("omitted", "ambiguous", "conflicting"):
        second = ((ctx.primary / "kitty-specs" / ctx.mission_dir.name) if scenario == "conflicting"
                  else ctx.linked / "kitty-specs" / "other-01M1MFE9")
        write_mission(second, "01M1MFE9ZZZZZZZZZZZZZZZZZZ")
        assert json.loads((second / "meta.json").read_text())["mission_id"] != json.loads(
            (ctx.mission_dir / "meta.json").read_text())["mission_id"]
    if scenario == "missing":
        selector = "missing-01M1NONE"
        assert not (ctx.linked / "kitty-specs" / selector).exists()
    elif scenario == "omitted":
        selector = None
        assert len(list((ctx.linked / "kitty-specs").glob("*/meta.json"))) == 2
    elif scenario == "ambiguous":
        selector = "01M1MFE9"
        ids = [json.loads(p.read_text())["mission_id"] for p in (ctx.linked / "kitty-specs").glob("*/meta.json")]
        assert len(set(ids)) == 2 and all(value.startswith(selector) for value in ids)
    elif scenario == "unsafe":
        selector = "../outside"
        assert not (ctx.linked / "outside").exists()
    assert locate_project_root(ctx.linked) == ctx.primary
    if scenario == "conflicting":
        with pytest.raises(MissionSurfaceConflictError):
            resolve_mission_operation_context(ctx.primary, selector, cwd=ctx.linked)
