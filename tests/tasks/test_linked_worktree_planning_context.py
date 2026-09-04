"""Executable contracts for planning from a caller-owned linked worktree."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.missions.operation_context import MissionSurfaceConflictError, resolve_mission_operation_context

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]

_SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
_MISSION_ID = "01M1MFE98JDK0S33WSYBQRPSDF"


@dataclass(frozen=True)
class LinkedMission:
    primary: Path
    linked: Path
    mission_dir: Path
    primary_head: str
    primary_status: str


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _write_mission(mission_dir: Path, mission_id: str = _MISSION_ID) -> None:
    for child in ("tasks", "checklists", "research", "contracts"):
        (mission_dir / child).mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": _SLUG, "slug": _SLUG,
                    "mission_type": "software-dev", "target_branch": "codex/task"}),
        encoding="utf-8",
    )
    (mission_dir / "spec.md").write_text(
        "# Linked Mission\n\n## Functional Requirements\n\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n| --- | --- | --- | --- |\n"
        "| FR-001 | Resolve a linked Mission. | Planning selects this checkout. | proposed |\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text(
        "# Implementation Plan\n\n## Technical Context\n\n**Language/Version**: Python 3.12\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")


@pytest.fixture
def linked_mission(tmp_path: Path) -> LinkedMission:
    primary = tmp_path / "repo"
    primary.mkdir()
    _git(primary, "init", "-q", "-b", "main")
    _git(primary, "config", "user.email", "test@example.invalid")
    _git(primary, "config", "user.name", "Test")
    (primary / "README.md").write_text("seed\n", encoding="utf-8")
    (primary / ".kittify" / "templates").mkdir(parents=True)
    (primary / ".kittify" / "config.yaml").write_text("project:\n  name: linked-test\n", encoding="utf-8")
    (primary / ".kittify" / "templates" / "plan-template.md").write_text(
        "# Implementation Plan\n\n## Technical Context\n\n**Language/Version**: Python 3.12\n",
        encoding="utf-8",
    )
    _git(primary, "add", ".")
    _git(primary, "commit", "-q", "-m", "init")

    linked = tmp_path / "linked"
    _git(primary, "worktree", "add", "-q", "-b", "codex/task", str(linked), "main")
    mission_dir = linked / "kitty-specs" / _SLUG
    _write_mission(mission_dir)
    _git(linked, "add", ".")
    _git(linked, "commit", "-q", "-m", "add linked mission")

    worktrees = _git(primary, "worktree", "list", "--porcelain").replace("\\", "/")
    assert "worktree " + str(linked).replace("\\", "/") in worktrees
    assert not (primary / "kitty-specs" / _SLUG).exists()
    return LinkedMission(primary, linked, mission_dir, _git(primary, "rev-parse", "HEAD"),
                         _git(primary, "status", "--porcelain"))


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    rows = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert rows, result.stdout + result.stderr
    return json.loads(rows[-1])


def _assert_primary_unchanged(ctx: LinkedMission) -> None:
    assert _git(ctx.primary, "rev-parse", "HEAD") == ctx.primary_head
    assert _git(ctx.primary, "status", "--porcelain") == ctx.primary_status
    assert not (ctx.primary / "kitty-specs" / _SLUG).exists()


@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_check_prerequisites_selects_linked_mission_by_stable_handle(
    linked_mission: LinkedMission, run_cli: Callable[..., subprocess.CompletedProcess[str]], selector: str
) -> None:
    result = run_cli(linked_mission.linked, "agent", "mission", "check-prerequisites",
                     "--mission", selector, "--paths-only", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["feature_dir"] == str(linked_mission.mission_dir)
    assert "available_missions" not in payload
    _assert_primary_unchanged(linked_mission)


def test_setup_plan_selects_the_same_linked_mission(
    linked_mission: LinkedMission, run_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    result = run_cli(linked_mission.linked, "agent", "mission", "setup-plan",
                     "--mission", _MISSION_ID, "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _payload(result)["feature_dir"] == str(linked_mission.mission_dir)
    _assert_primary_unchanged(linked_mission)


def test_decision_open_and_verify_use_linked_identity(
    linked_mission: LinkedMission, run_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    opened = run_cli(linked_mission.linked, "agent", "decision", "open", "--mission", _MISSION_ID,
                     "--flow", "plan", "--input-key", "resolver",
                     "--question", "Which Mission surface is authoritative?", "--json")
    assert opened.returncode == 0, opened.stdout + opened.stderr
    assert _payload(opened)["mission_id"] == _MISSION_ID
    verified = run_cli(linked_mission.linked, "agent", "decision", "verify", "--mission", _SLUG,
                       "--no-fail-on-stale", "--json")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    _assert_primary_unchanged(linked_mission)


def test_spec_commit_never_selects_protected_primary(
    linked_mission: LinkedMission, run_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    plan = linked_mission.mission_dir / "plan.md"
    plan.write_text(plan.read_text(encoding="utf-8") + "\nLinked edit.\n", encoding="utf-8")
    result = run_cli(linked_mission.linked, "spec-commit", str(plan), "--message",
                     "test linked spec commit", "--mission", _MISSION_ID,
                     "--target-branch", "codex/task", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "protected branch 'main'" not in result.stdout + result.stderr
    _assert_primary_unchanged(linked_mission)


def test_conflicting_primary_and_linked_identities_fail_closed(linked_mission: LinkedMission) -> None:
    _write_mission(linked_mission.primary / "kitty-specs" / _SLUG,
                   mission_id="01M1MFE9ZZZZZZZZZZZZZZZZZZ")
    with pytest.raises(MissionSurfaceConflictError):
        resolve_mission_operation_context(linked_mission.primary, _SLUG, cwd=linked_mission.linked)
    assert _git(linked_mission.primary, "rev-parse", "HEAD") == linked_mission.primary_head


@pytest.mark.parametrize("selector", ["missing-01M1NONE", "../unsafe"])
def test_invalid_selectors_fail_without_mutating_primary(
    linked_mission: LinkedMission, run_cli: Callable[..., subprocess.CompletedProcess[str]], selector: str
) -> None:
    result = run_cli(linked_mission.linked, "agent", "mission", "check-prerequisites",
                     "--mission", selector, "--paths-only", "--json")
    assert result.returncode != 0
    _assert_primary_unchanged(linked_mission)
