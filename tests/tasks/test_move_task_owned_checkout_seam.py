"""Owned-checkout seam for ``agent tasks move-task`` (issue 26, WP01).

The executable oracle for FR-001/FR-002/FR-004/FR-005 of
``tasks-status-owned-checkout-seam-01M282V3``:

* **T001** — a mission that lives in a real linked (owned) worktree records its
  lane transition in that checkout's canonical status log when the caller
  declares ``--owned-checkout``.
* **T004** — an undeclared run still fails closed (``mission_not_found``), and a
  checkout that is not a worktree of the resolved primary is refused with the
  shared typed ownership error. Neither refusal writes anything.
* **T005** — the primary checkout's HEAD, index and file set are unchanged by
  every acceptance run (NFR-004 / FR-004).
* **T006** — the guarded path still refuses from a worktree when no checkout is
  declared (C-001: the option is honoured only when declared).

The fixture is deliberately REAL — a registered linked worktree of a temporary
primary, holding an actual ``kitty-specs/<slug>/`` mission with ``meta.json``,
``tasks.md`` and a WP file. A temp-directory shortcut would not reproduce the
defect, which is about git topology and the primary fold it drives.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

MISSION_ID = "01M282V3ZTZNZDDD40BSZ7B6SH"
MISSION_SLUG = "owned-move-task-seam-" + MISSION_ID[:8]
OWNED_BRANCH = "codex/owned-move-task-seam"


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
    "friendly_name": "Owned move-task seam fixture",
    "mission_id": MISSION_ID,
    "mission_number": None,
    "mission_slug": MISSION_SLUG,
    "mission_type": "software-dev",
    "purpose_context": "Fixture mission that lives only in the owned checkout.",
    "purpose_tldr": "Owned move-task seam fixture.",
    "slug": MISSION_SLUG,
    "target_branch": OWNED_BRANCH,
    "topology": "single_branch",
}

_WP01 = """---
work_package_id: "WP01"
title: "Owned move-task seam fixture"
dependencies: []
subtasks:
  - T001
owned_files:
  - "docs/owned-seam.md"
execution_mode: "code_change"
planning_base_branch: "codex/owned-move-task-seam"
merge_target_branch: "codex/owned-move-task-seam"
---

# WP01 - owned move-task seam fixture
"""

_TASKS_MD = """# Work Packages: Owned move-task seam fixture

---

## Work Package WP01: Owned move-task seam fixture

**Dependencies**: None
**Subtasks**: T001
"""


def _init_owned_mission(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a primary repo plus a real linked worktree that owns a mission.

    The mission directory exists ONLY in the owned checkout — the primary has no
    ``kitty-specs/<slug>/`` at all — which is what makes the ambient-root fold
    observable.
    """
    primary = tmp_path / "primary"
    owned = tmp_path / "owned-checkout"
    (primary / ".kittify").mkdir(parents=True)
    (primary / ".kittify" / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n", encoding="utf-8"
    )
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
    (mission_dir / "meta.json").write_text(
        json.dumps(_META, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (mission_dir / "tasks.md").write_text(_TASKS_MD, encoding="utf-8")
    (mission_dir / "tasks" / "WP01-owned-seam.md").write_text(_WP01, encoding="utf-8")
    _seed_status_log(mission_dir)
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Add owned mission")
    return primary, owned, mission_dir



#: The canonical first record every mission gets in its status log. Recorded here
#: verbatim (same key set the real writer emits) because the fixture cannot run
#: `finalize-tasks`; without it `move-task` refuses with "WP WP01 has no canonical
#: status in feature ...", which is a DIFFERENT failure than the one under test.
_GENESIS_EVENT: dict[str, Any] = {
    "actor": "codex",
    "at": "2026-09-11T11:15:01.000000+00:00",
    "event_id": "01M282V4000000000000000001",
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

def _seed_status_log(mission_dir: Path) -> None:
    (mission_dir / "status.events.jsonl").write_text(
        json.dumps(_GENESIS_EVENT, sort_keys=True) + "\n", encoding="utf-8"
    )


def _events(mission_dir: Path) -> list[dict[str, Any]]:
    log = mission_dir / "status.events.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def _lanes(mission_dir: Path) -> list[str]:
    """The lane transitions recorded in the mission log, in order.

    The log also carries annotation records (the dispatch-binding sidecars
    `move-task` appends), which have no lane fields at all - the oracle only
    cares about the transitions.
    """
    return [event["to_lane"] for event in _events(mission_dir) if "to_lane" in event]


def _invoke(args: list[str]) -> Any:
    return runner.invoke(tasks_app, args)


def test_move_task_records_transition_in_the_owned_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T001/T002: a declared owned checkout owns the write (issue 26)."""
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"] == "success"
    assert payload["transition_applied"] is True
    assert payload["new_lane"] == "in_progress"

    # move-task claims the package and then moves it, so the log reads
    # genesis -> planned -> claimed -> in_progress.
    assert _lanes(mission_dir) == ["planned", "claimed", "in_progress"]
    assert _events(mission_dir)[-1]["mission_slug"] == MISSION_SLUG

    # Every path the command reports is the checkout it was told to own.
    assert Path(payload["status_events_path"]) == mission_dir / "status.events.jsonl"
    assert Path(payload["path"]).is_relative_to(owned)

    # T005: the primary checkout is untouched - not even a mission directory.
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status
    assert not (primary / "kitty-specs" / MISSION_SLUG).exists()


def test_move_task_without_declaration_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T004/T006: no declaration, no owned routing - typed refusal, no write."""
    primary, _owned, mission_dir = _init_owned_mission(tmp_path)
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(["move-task", "WP01", "--to", "doing", "--mission", MISSION_SLUG, "--json"])

    assert result.exit_code != 0
    # The usage/mission-not-found envelope renders through the error path (its
    # text lands on stderr), so assert against the combined stream.
    assert "mission_not_found" in (result.output + (result.stderr or ""))
    # Only the seeded genesis record is present: nothing was appended.
    assert _lanes(mission_dir) == ["planned"]
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status


def test_move_task_refuses_a_checkout_that_is_not_owned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T004: a foreign directory is refused through the shared typed refusal."""
    primary, _owned, mission_dir = _init_owned_mission(tmp_path)
    foreign = tmp_path / "foreign-checkout"
    foreign.mkdir()
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(primary)
    result = _invoke(
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(foreign),
            "--json",
        ]
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert payload["error_code"]
    assert _lanes(mission_dir) == ["planned"]
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status


def test_move_task_declared_from_the_owned_checkout_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T002: the operator may stand IN the owned checkout and declare it too."""
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    primary_head, primary_status = _head(primary), _porcelain(primary)

    monkeypatch.chdir(owned)
    result = _invoke(
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--mission",
            MISSION_SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ]
    )

    assert result.exit_code == 0, result.stdout
    # move-task claims the package and then moves it, so the log reads
    # genesis -> planned -> claimed -> in_progress.
    assert _lanes(mission_dir) == ["planned", "claimed", "in_progress"]
    assert _head(primary) == primary_head
    assert _porcelain(primary) == primary_status
