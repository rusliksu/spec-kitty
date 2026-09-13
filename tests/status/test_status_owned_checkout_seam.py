"""Owned-checkout seam for the canonical status commands (issue 26, WP01).

The status half of the executable oracle for FR-002/FR-003/FR-004/FR-005 of
``tasks-status-owned-checkout-seam-01M282V3``:

* a state-recording ``agent status emit`` that declares ``--owned-checkout`` writes the
  event into the owned checkout and reports that path back (D-12 recorded the
  opposite outcome - the event landing in the protected primary - as the hazard
  this seam exists to close);
* an undeclared run still fails closed and writes nothing;
* a declaration that is not a worktree of the resolved primary is refused with
  the shared typed error and writes nothing;
* the primary checkout is byte-identical afterwards (NFR-004).

The fixture is a real registered linked worktree holding a real mission, for the
same reason as the move-task module: the defect is a git-topology fold, so a
temp-directory shortcut would not reproduce it.
"""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app as status_app

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

MISSION_ID = "01M282V3ZTZNZDDD40BSZ7B6SH"
MISSION_SLUG = "owned-status-seam-" + MISSION_ID[:8]
OWNED_BRANCH = "codex/owned-status-seam"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


def _porcelain(repo: Path) -> str:
    return _git(repo, "status", "--porcelain", "--untracked-files=all")


_META: dict[str, Any] = {
    "created_at": "2026-09-11T11:15:00.224422+00:00",
    "flattened": False,
    "friendly_name": "Owned status seam fixture",
    "mission_id": MISSION_ID,
    "mission_number": None,
    "mission_slug": MISSION_SLUG,
    "mission_type": "software-dev",
    "purpose_context": "Fixture mission that lives only in the owned checkout.",
    "purpose_tldr": "Owned status seam fixture.",
    "slug": MISSION_SLUG,
    "target_branch": OWNED_BRANCH,
    "topology": "single_branch",
}

#: The canonical first record every mission gets in its status log, recorded in
#: the same shape the real writer emits. Without it the emitter refuses with a
#: "no canonical status" error, which is a different failure than the one under
#: test.
_GENESIS_EVENT: dict[str, Any] = {
    "actor": "codex",
    "at": "2026-09-11T11:15:01.000000+00:00",
    "event_id": "01M282V4000000000000000002",
    "evidence": None,
    "execution_mode": "worktree",
    "force": False,
    "from_lane": "genesis",
    "mission_id": MISSION_ID,
    "mission_slug": MISSION_SLUG,
    "policy_metadata": None,
    "reason": None,
    "review_ref": None,
    "to_lane": "planned",
    "wp_id": "WP01",
}

_WP01 = """---
work_package_id: "WP01"
title: "Owned status seam fixture"
dependencies: []
subtasks:
  - T001
execution_mode: "code_change"
planning_base_branch: "codex/owned-status-seam"
merge_target_branch: "codex/owned-status-seam"
---

# WP01 - owned status seam fixture
"""

_TASKS_MD = """# Work Packages: Owned status seam fixture

---

## Work Package WP01: Owned status seam fixture

**Dependencies**: None
**Subtasks**: T001
"""


def _init_owned_mission(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a primary repo plus a real linked worktree that owns a mission.

    The mission directory exists ONLY in the owned checkout, so any lookup that
    folds to the ambient primary cannot find it.
    """
    primary = tmp_path / "primary"
    owned = tmp_path / "owned-checkout"
    (primary / ".kittify").mkdir(parents=True)
    (primary / ".kittify" / "config.yaml").write_text("mission_type_activations:\n  - software-dev\n", encoding="utf-8")
    (primary / "kitty-specs").mkdir()
    (primary / "kitty-specs" / ".gitkeep").touch()

    _git(primary, "init", "--initial-branch=main")
    _git(primary, "config", "user.name", "Spec Kitty Tests")
    _git(primary, "config", "user.email", "spec-kitty-tests@example.invalid")
    _git(primary, "add", ".")
    _git(primary, "commit", "-m", "Initial project")

    _git(primary, "worktree", "add", "-b", OWNED_BRANCH, str(owned))

    mission_dir = owned / "kitty-specs" / MISSION_SLUG
    (mission_dir / "tasks").mkdir(parents=True)
    (mission_dir / "meta.json").write_text(json.dumps(_META, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (mission_dir / "tasks.md").write_text(_TASKS_MD, encoding="utf-8")
    (mission_dir / "tasks" / "WP01-owned-seam.md").write_text(_WP01, encoding="utf-8")
    (mission_dir / "status.events.jsonl").write_text(json.dumps(_GENESIS_EVENT, sort_keys=True) + "\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add owned mission")
    return primary, owned, mission_dir


def _lanes(mission_dir: Path) -> list[str]:
    log = mission_dir / "status.events.jsonl"
    if not log.exists():
        return []
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    return [event["to_lane"] for event in events if "to_lane" in event]


def _invoke(args: list[str]) -> Any:
    return runner.invoke(status_app, args)


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


def _enter_review(owned: Path) -> None:
    from specify_cli.status import Lane, WPInnerStateDelta, emit_inner_state_changed

    for lane, actor, extra in (
        ("claimed", "fixture-implementer", []),
        ("in_progress", "fixture-implementer", ["--workspace-context", str(owned)]),
        ("for_review", "fixture-implementer", ["--subtasks-complete", "--implementation-evidence-present"]),
        ("in_review", "fixture-reviewer", []),
    ):
        if lane == "for_review":
            emit_inner_state_changed(
                owned / "kitty-specs" / MISSION_SLUG,
                "WP01",
                WPInnerStateDelta(subtasks={"T001": Lane.DONE}),
                actor="fixture-implementer",
                mission_slug=MISSION_SLUG,
                repo_root=owned,
                effective_root=owned,
            )
        result = _invoke(["emit", "WP01", "--to", lane, "--actor", actor, "--mission", MISSION_SLUG, "--owned-checkout", str(owned), "--json", *extra])
        assert result.exit_code == 0, result.output


@pytest.mark.parametrize("command", ["emit", "list-tasks"])
def test_owned_mission_divergence_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    from specify_cli.cli.commands.agent.tasks import app as tasks_app

    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    copy = primary / "kitty-specs" / MISSION_SLUG
    shutil.copytree(mission_dir, copy)
    (copy / "tasks.md").write_text("Different primary task index\n", encoding="utf-8")
    before = _file_bytes(primary)
    monkeypatch.chdir(primary)
    args = [command, "--mission", MISSION_SLUG, "--owned-checkout", str(owned), "--json"]
    if command == "emit":
        args += ["WP01", "--to", "claimed", "--actor", "codex"]
    result = runner.invoke(status_app if command == "emit" else tasks_app, args)
    assert result.exit_code == 0, result.output
    assert "owned_mission_divergence" in result.stderr
    json.loads(result.stdout)  # The diagnostic must not corrupt the JSON envelope.
    assert _file_bytes(primary) == before


def test_incomplete_owned_subtasks_refuse_review_even_with_completion_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    monkeypatch.chdir(primary)
    common = ["WP01", "--actor", "fixture-implementer", "--mission", MISSION_SLUG, "--owned-checkout", str(owned), "--json"]
    for lane in ("claimed", "in_progress"):
        result = _invoke(["emit", "--to", lane, "--workspace-context", str(owned), *common])
        assert result.exit_code == 0, result.output
    before = {root: _file_bytes(root) for root in (primary, owned)}
    result = _invoke(["emit", "--to", "for_review", "--subtasks-complete", "--implementation-evidence-present", *common])
    assert result.exit_code == 1, result.output
    assert "requires completed subtasks" in result.output
    assert _lanes(mission_dir)[-1] == "in_progress"
    for root, expected in before.items():
        assert _file_bytes(root) == expected


@pytest.mark.parametrize("command", ["validate", "lifecycle"])
@pytest.mark.parametrize("declaration", ["owned", "absent", "foreign"])
def test_status_read_commands_honour_explicit_ownership_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, declaration: str) -> None:
    from specify_cli.status.reducer import materialize

    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    materialize(mission_dir)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _git(foreign, "init")
    monkeypatch.chdir(owned if declaration == "absent" else primary)
    before = {root: _file_bytes(root) for root in (primary, owned, foreign)}
    primary_head, primary_index = _head(primary), _git(primary, "ls-files", "--stage")
    args = [command, "--mission", MISSION_SLUG, "--json"]
    if declaration != "absent":
        args += ["--owned-checkout", str(owned if declaration == "owned" else foreign)]
    result = _invoke(args)
    if declaration == "owned":
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["mission_slug"] == MISSION_SLUG
        if command == "lifecycle":
            assert payload["total_wps"] == 1
        else:
            assert payload["passed"] is True
    else:
        assert result.exit_code != 0
    for root, expected in before.items():
        assert _file_bytes(root) == expected
    assert _head(primary) == primary_head
    assert _git(primary, "ls-files", "--stage") == primary_index


@pytest.mark.parametrize("valid", [True, False])
def test_owned_review_verdict_is_recorded_or_refused_without_foreign_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid: bool) -> None:
    """Catch lost review payloads and invalid verdicts that still mutate status."""
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    monkeypatch.chdir(primary)
    primary_before, primary_head = _file_bytes(primary), _head(primary)
    _enter_review(owned)
    owned_before = _file_bytes(owned)
    verdict = {"reviewer": "fixture-reviewer", "verdict": "approved", "reference": "test://independent-review"}
    if not valid:
        verdict.pop("reviewer")
    result = _invoke(
        [
            "emit",
            "WP01",
            "--to",
            "approved",
            "--actor",
            "fixture-reviewer",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(owned),
            "--review-result-json",
            json.dumps(verdict),
            "--json",
        ]
    )
    assert result.exit_code == (0 if valid else 1), result.output
    assert _file_bytes(primary) == primary_before
    assert _head(primary) == primary_head
    if valid:
        events = [json.loads(line) for line in (mission_dir / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
        approval = next(event for event in reversed(events) if event.get("to_lane") == "approved")
        assert approval["review_result"] == verdict
        snapshot = json.loads((mission_dir / "status.json").read_text(encoding="utf-8"))
        assert snapshot["work_packages"]["WP01"]["lane"] == "approved"
    else:
        assert "reviewer" in json.loads(result.output)["error"].lower()
        assert _file_bytes(owned) == owned_before
        assert _lanes(mission_dir)[-1] == "in_review"


def test_status_emit_records_the_event_in_the_owned_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A declared owned checkout owns the write, and reports that path back."""
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(
        [
            "emit",
            "WP01",
            "--to",
            "claimed",
            "--actor",
            "codex",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["to_lane"] == "claimed"
    # D-12 recorded this path pointing at the protected primary; it must now
    # name the log this command actually wrote.
    assert Path(payload["status_events_path"]) == mission_dir / "status.events.jsonl"

    assert _lanes(mission_dir) == ["planned", "claimed"]

    # NFR-004: the primary checkout is untouched, and holds no mission dir.
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()


def test_status_emit_without_declaration_still_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No declaration, no owned routing: refusal, and nothing appended."""
    primary, _owned, mission_dir = _init_owned_mission(tmp_path)
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(
        [
            "emit",
            "WP01",
            "--to",
            "claimed",
            "--actor",
            "codex",
            "--mission",
            MISSION_SLUG,
            "--json",
        ]
    )

    assert result.exit_code != 0
    assert _lanes(mission_dir) == ["planned"]
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status


def test_status_emit_refuses_a_checkout_that_is_not_owned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A foreign directory is refused through the shared typed refusal."""
    primary, _owned, mission_dir = _init_owned_mission(tmp_path)
    foreign = tmp_path / "foreign-checkout"
    foreign.mkdir()
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(
        [
            "emit",
            "WP01",
            "--to",
            "claimed",
            "--actor",
            "codex",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(foreign),
            "--json",
        ]
    )

    assert result.exit_code != 0
    assert _lanes(mission_dir) == ["planned"]
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status
