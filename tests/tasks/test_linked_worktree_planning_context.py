"""Executable contracts for planning from a caller-owned linked worktree."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from specify_cli.missions.operation_context import MissionSurfaceConflictError, resolve_mission_operation_context
from tests.tasks.linked_worktree_harness import (
    LinkedMission as VerifiedLinkedMission,
    create_linked_mission,
    git as _git,
    snapshot_primary,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox, pytest.mark.real_worktree_detection]

_SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
_MISSION_ID = "01M1MFE98JDK0S33WSYBQRPSDF"


@dataclass(frozen=True)
class LinkedMission(VerifiedLinkedMission):
    """Preserve the exported mixed-contract fixture fields for allocation tests."""
    primary_head: str
    primary_status: str


def _write_mission(mission_dir: Path, mission_id: str = _MISSION_ID) -> None:
    for child in ("tasks", "checklists", "research", "contracts"):
        (mission_dir / child).mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": mission_dir.name, "slug": mission_dir.name,
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
def linked_mission(tmp_path: Path) -> Iterator[LinkedMission]:
    verified = create_linked_mission(tmp_path)
    primary, linked, mission_dir = verified.primary, verified.linked, verified.mission_dir
    # Keep this older integration contract's pre-WP state: its individual nodes
    # seed their own WPs, event history, and branch gates.
    (mission_dir / "tasks" / "WP01.md").unlink()
    (mission_dir / "status.json").unlink(missing_ok=True)
    _write_mission(mission_dir)
    for checkout in (primary, linked):
        (checkout / ".kittify/templates/plan-template.md").write_bytes((mission_dir / "plan.md").read_bytes())
        config = checkout / ".kittify/config.yaml"
        config.write_text(config.read_text(encoding="utf-8") + "mission_type_activations:\n  - software-dev\n", encoding="utf-8")
        _git(checkout, "add", ".kittify")
        _git(checkout, "commit", "-q", "-m", "prepare mixed-contract templates and activation")
    _git(linked, "add", ".")
    _git(linked, "commit", "-q", "-m", "add linked mission")

    worktrees = _git(primary, "worktree", "list", "--porcelain").replace("\\", "/")
    assert "worktree " + str(linked).replace("\\", "/") in worktrees
    assert not (primary / "kitty-specs" / _SLUG).exists()
    ctx = LinkedMission(primary, linked, mission_dir, _git(primary, "rev-parse", "HEAD"),
                        _git(primary, "status", "--porcelain"))
    yield ctx
    # Teardown runs even when a command's success assertion fails.
    assert _git(primary, "rev-parse", "HEAD") == ctx.primary_head


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    rows = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert rows, result.stdout + result.stderr
    return cast(dict[str, object], json.loads(rows[-1]))


@pytest.fixture
def checked_cli(
    linked_mission: LinkedMission,
    run_cli: Callable[..., subprocess.CompletedProcess[str]],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Check primary bytes, index, and HEAD for every command, including failures."""
    def invoke(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        before = snapshot_primary(linked_mission.primary)
        try:
            return run_cli(project, *args)
        finally:
            assert snapshot_primary(linked_mission.primary) == before, "Command mutated the primary checkout"

    return invoke


def _assert_primary_unchanged(ctx: LinkedMission) -> None:
    assert _git(ctx.primary, "rev-parse", "HEAD") == ctx.primary_head
    assert _git(ctx.primary, "status", "--porcelain") == ctx.primary_status
    assert not (ctx.primary / "kitty-specs" / _SLUG).exists()


@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_record_analysis_persists_in_selected_worktree(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]], selector: str,
) -> None:
    """Catch primary re-anchoring in selection, persistence, and commit placement."""
    from specify_cli.analysis_report import check_analysis_report_current

    report_input = linked_mission.linked.parent / "analysis-input.md"
    report_input.write_text(
        "---\nschema: analysis-findings/v1\nfindings: []\n"
        "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n---\n"
        "# Specification Analysis Report\n\nFixture has no blocking findings.\n",
        encoding="utf-8",
    )
    result = checked_cli(linked_mission.linked, "agent", "mission", "record-analysis",
                         "--mission", selector, "--input-file", str(report_input), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    report = linked_mission.mission_dir / "analysis-report.md"
    assert _payload(result)["path"] == str(report)
    assert "Fixture has no blocking findings." in report.read_text(encoding="utf-8")
    assert check_analysis_report_current(linked_mission.mission_dir, linked_mission.linked).ok
    relative_report = report.relative_to(linked_mission.linked).as_posix()
    assert _git(linked_mission.linked, "show", "--pretty=", "--name-only", "HEAD") == relative_report
    assert _git(linked_mission.linked, "status", "--porcelain") == ""
    _assert_primary_unchanged(linked_mission)
    # A meaningful input mutation must invalidate the persisted acceptance result.
    spec_path = linked_mission.mission_dir / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\nNew requirement.\n", encoding="utf-8")
    stale = check_analysis_report_current(linked_mission.mission_dir, linked_mission.linked)
    assert not stale.ok
    assert "spec.md" in stale.mismatches


def test_linked_analysis_gate_uses_owned_hash_root(linked_mission: LinkedMission) -> None:
    """A valid persisted report must not become stale by hashing another checkout."""
    from specify_cli.analysis_report import write_analysis_report
    from specify_cli.cli.commands.agent.workflow_executor import implement_resolve_feedback_and_gate
    from specify_cli.task_utils import WorkPackage

    write_analysis_report(
        feature_dir=linked_mission.mission_dir, repo_root=linked_mission.linked,
        body="---\nschema: analysis-findings/v1\nfindings: []\n"
             "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n---\n# Analysis\n",
    )
    wp = WorkPackage(
        feature=_SLUG, path=linked_mission.mission_dir / "tasks" / "WP01.md",
        current_lane="planned", relative_subpath=Path("WP01.md"),
        frontmatter="", body="", padding="",
    )
    result = implement_resolve_feedback_and_gate(
        linked_mission.primary, _SLUG, "WP01", wp, effective_root=linked_mission.linked,
    )
    assert result[0] == linked_mission.mission_dir
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("refusal", ["missing", "ambiguous", "conflict", "dirty"])
def test_record_analysis_refuses_unsafe_context(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]], refusal: str,
) -> None:
    selector = _SLUG
    if refusal == "missing":
        selector = "missing-01M1NONE"
    elif refusal == "ambiguous":
        selector = "01M1MFE9"
        _write_mission(linked_mission.linked / "kitty-specs" / "other-01M1MFE9",
                       "01M1MFE9ZZZZZZZZZZZZZZZZZZ")
    elif refusal == "conflict":
        _write_mission(linked_mission.primary / "kitty-specs" / _SLUG,
                       "01M1MFE9ZZZZZZZZZZZZZZZZZZZZ")
    else:
        (linked_mission.linked / "README.md").write_text("unrelated edit\n", encoding="utf-8")
    result = checked_cli(linked_mission.linked, "agent", "mission", "record-analysis",
                         "--mission", selector, "--input-file", "not-read.md", "--json")
    assert result.returncode != 0
    payload = _payload(result)
    if refusal == "dirty":
        assert payload.get("error_code") == "DIRTY_WORKTREE", payload
    elif refusal == "conflict":
        assert "different identities" in str(payload["error"])
    else:
        assert payload.get("error_code")
    assert not (linked_mission.mission_dir / "analysis-report.md").exists()
    assert not (linked_mission.primary / "kitty-specs" / _SLUG / "analysis-report.md").exists()


@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_check_prerequisites_selects_linked_mission_by_stable_handle(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]], selector: str
) -> None:
    result = checked_cli(linked_mission.linked, "agent", "mission", "check-prerequisites",
                     "--mission", selector, "--paths-only", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["feature_dir"] == str(linked_mission.mission_dir)
    assert "available_missions" not in payload
    _assert_primary_unchanged(linked_mission)


def test_prerequisites_report_caller_branch(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    result = checked_cli(linked_mission.linked, "agent", "mission", "check-prerequisites",
                         "--mission", _SLUG, "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["current_branch"] == "codex/task"
    assert payload["target_branch"] == "codex/task"


@pytest.mark.parametrize("consumer", ["workflow", "tasks"])
@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_lifecycle_command_selector_keeps_linked_mission(
    linked_mission: LinkedMission, monkeypatch: pytest.MonkeyPatch,
    consumer: str, selector: str,
) -> None:
    from specify_cli.cli.commands.agent import tasks_shared, workflow

    monkeypatch.chdir(linked_mission.linked)
    resolve = workflow._find_mission_slug if consumer == "workflow" else tasks_shared._find_mission_slug
    assert resolve(explicit_mission=selector, repo_root=linked_mission.primary) == _SLUG
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("consumer", ["workflow", "tasks"])
def test_lifecycle_command_selector_refuses_conflicting_identity(
    linked_mission: LinkedMission, monkeypatch: pytest.MonkeyPatch, consumer: str,
) -> None:
    from specify_cli.cli.commands.agent import tasks_shared, workflow

    _write_mission(linked_mission.primary / "kitty-specs" / _SLUG,
                   mission_id="01M1MFE9ZZZZZZZZZZZZZZZZZZ")
    monkeypatch.chdir(linked_mission.linked)
    resolve = workflow._find_mission_slug if consumer == "workflow" else tasks_shared._find_mission_slug
    with pytest.raises(MissionSurfaceConflictError):
        resolve(explicit_mission=_SLUG, repo_root=linked_mission.primary)


@pytest.mark.parametrize("consumer", ["workflow", "tasks"])
@pytest.mark.parametrize("selector", ["missing-01M1NONE", "01M1MFE9"])
def test_lifecycle_command_selector_refuses_missing_or_ambiguous(
    linked_mission: LinkedMission, monkeypatch: pytest.MonkeyPatch, consumer: str, selector: str,
) -> None:
    from specify_cli.cli.commands.agent import tasks_shared, workflow

    _write_mission(linked_mission.linked / "kitty-specs" / "other-01M1MFE9",
                   mission_id="01M1MFE9ZZZZZZZZZZZZZZZZZZ")
    monkeypatch.chdir(linked_mission.linked)
    resolve = workflow._find_mission_slug if consumer == "workflow" else tasks_shared._find_mission_slug
    with pytest.raises(SystemExit) as error:
        resolve(explicit_mission=selector, repo_root=linked_mission.primary)
    assert error.value.code == 2
    _assert_primary_unchanged(linked_mission)


def test_setup_plan_selects_the_same_linked_mission(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    result = checked_cli(linked_mission.linked, "agent", "mission", "setup-plan",
                     "--mission", _MISSION_ID, "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _payload(result)["feature_dir"] == str(linked_mission.mission_dir)
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("has_dependency", [True, False])
def test_linked_implement_reaches_dependency_gate_without_mutation(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]],
    has_dependency: bool,
) -> None:
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.store import append_event

    mission_dir = linked_mission.mission_dir
    (mission_dir / "tasks" / "WP01-blocked.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Blocked implementation\n"
        "execution_mode: code_change\nowned_files:\n- src/recovery.py\n"
        + ("dependencies:\n- WP00\n" if has_dependency else "dependencies: []\n")
        + "---\n\n# Blocked implementation\n", encoding="utf-8",
    )
    append_event(mission_dir, StatusEvent(
        event_id="01M1MFE98JDK0S33WSYBQRPSDG", mission_slug=_SLUG, wp_id="WP01",
        from_lane=Lane.PLANNED, to_lane=Lane.PLANNED, at="2026-09-04T00:00:00+00:00",
        actor="fixture", force=False, execution_mode="worktree", mission_id=_MISSION_ID,
    ))
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "seed dependency gate")
    events_before = (mission_dir / "status.events.jsonl").read_bytes()
    result = checked_cli(linked_mission.linked, "agent", "action", "implement", "WP01",
                         "--mission", _MISSION_ID, "--agent", "codex")
    assert result.returncode != 0
    expected_gate = "dependencies_not_satisfied" if has_dependency else "analysis_report_required"
    assert expected_gate in result.stdout + result.stderr
    if not has_dependency:
        assert str(mission_dir / "analysis-report.md") in result.stdout
    assert "Branch: codex/task (target for this mission)" in result.stdout
    assert (mission_dir / "status.events.jsonl").read_bytes() == events_before
    assert not (linked_mission.primary / ".worktrees").exists()
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_implement_preserves_anchor_through_workspace_gate(
    linked_mission: LinkedMission,
    checked_cli: Callable[..., subprocess.CompletedProcess[str]],
    selector: str,
) -> None:
    """After analysis, workspace lookup must reach the owned manifest guard."""
    from specify_cli.analysis_report import write_analysis_report
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.store import append_event

    mission_dir = linked_mission.mission_dir
    (mission_dir / "tasks" / "WP01-workspace.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Workspace gate\n"
        "execution_mode: code_change\nowned_files:\n- src/recovery.py\n"
        "dependencies: []\n---\n\n# Workspace gate\n", encoding="utf-8",
    )
    append_event(mission_dir, StatusEvent(
        event_id="01M1MFE98JDK0S33WSYBQRPSDG", mission_slug=_SLUG, wp_id="WP01",
        from_lane=Lane.PLANNED, to_lane=Lane.PLANNED, at="2026-09-04T00:00:00+00:00",
        actor="fixture", force=False, execution_mode="worktree", mission_id=_MISSION_ID,
    ))
    write_analysis_report(
        feature_dir=mission_dir, repo_root=linked_mission.linked,
        body="---\nschema: analysis-findings/v1\nfindings: []\n"
             "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n---\n# Analysis\n",
    )
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "seed post-analysis workspace gate")
    events_before = (mission_dir / "status.events.jsonl").read_bytes()

    result = checked_cli(linked_mission.linked, "agent", "action", "implement", "WP01",
                         "--mission", selector, "--agent", "codex")

    # The fixture deliberately omits lanes.json. This is a real safety guard,
    # not an allocation mock: no WP claim or workspace may be created.
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert f"lanes.json is required for {mission_dir}" in output
    assert (mission_dir / "status.events.jsonl").read_bytes() == events_before
    assert not (linked_mission.primary / ".worktrees").exists()
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("action", ["implement", "review"])
@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_lifecycle_context_selects_linked_wp(
    linked_mission: LinkedMission,
    checked_cli: Callable[..., subprocess.CompletedProcess[str]],
    action: str,
    selector: str,
) -> None:
    """WP-bearing reads must keep the Mission selected by the CLI boundary."""
    from specify_cli.lanes.models import ExecutionLane, LanesManifest
    from specify_cli.lanes.persistence import write_lanes_json

    mission_dir = linked_mission.mission_dir
    wp_path = mission_dir / "tasks" / "WP01-recovery.md"
    wp_path.write_text(
        "---\nwork_package_id: WP01\ntitle: Lifecycle recovery\n"
        "execution_mode: code_change\nowned_files:\n- src/recovery.py\n"
        "dependencies: []\n---\n\n# Lifecycle recovery\n",
        encoding="utf-8",
    )
    write_lanes_json(mission_dir, LanesManifest(
        version=1, mission_slug=_SLUG, mission_id=_MISSION_ID,
        mission_branch=f"kitty/mission-{_SLUG}", target_branch="codex/task",
        lanes=[ExecutionLane("lane-a", ("WP01",), ("src/recovery.py",), (), (), 0)],
        computed_at="2026-09-04T00:00:00+00:00", computed_from="dependency_graph+ownership",
    ))
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "seed lifecycle contract")

    result = checked_cli(
        linked_mission.linked, "agent", "context", "resolve", "--action", action,
        "--mission", selector, "--wp-id", "WP01", "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["wp_file"] == str(wp_path)
    assert payload["wp_id"] == "WP01"
    assert payload["lane_id"] == "lane-a"
    assert payload["execution_mode"] == "code_change"
    assert payload["resolution_kind"] == "lane_workspace"
    assert Path(payload["workspace_path"]).parent == linked_mission.primary / ".worktrees"
    _assert_primary_unchanged(linked_mission)


def test_decision_open_uses_linked_identity(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    opened = checked_cli(linked_mission.linked, "agent", "decision", "open", "--mission", _MISSION_ID,
                     "--flow", "plan", "--input-key", "resolver",
                     "--slot-key", "resolver-surface",
                     "--question", "Which Mission surface is authoritative?", "--json")
    assert opened.returncode == 0, opened.stdout + opened.stderr
    payload = _payload(opened)
    assert payload["mission_id"] == _MISSION_ID
    artifact = Path(str(payload["artifact_path"]))
    if not artifact.is_absolute():
        artifact = linked_mission.linked / artifact
    assert artifact.resolve().is_relative_to(linked_mission.mission_dir.resolve())
    assert artifact.is_file()
    events = (linked_mission.mission_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert str(payload["decision_id"]) in events
    _assert_primary_unchanged(linked_mission)


def test_decision_verify_reads_linked_mission_independently(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    verified = checked_cli(linked_mission.linked, "agent", "decision", "verify", "--mission", _SLUG,
                       "--no-fail-on-stale", "--json")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("selector", [_SLUG, _MISSION_ID])
def test_mark_status_records_subtasks_on_selected_planning_surface(
    linked_mission: LinkedMission,
    checked_cli: Callable[..., subprocess.CompletedProcess[str]],
    selector: str,
) -> None:
    """Lifecycle bookkeeping must use the same selected Mission as planning."""
    from specify_cli.status import Lane
    from specify_cli.status.store import read_event_stream

    tasks_md = linked_mission.mission_dir / "tasks.md"
    tasks_md.write_text(
        "# Tasks\n\n"
        "- [ ] T009 (WP03) Adopt decision context.\n"
        "- [ ] T010 (WP03) Adopt commit context.\n"
        "- [ ] T011 (WP03) Verify regressions.\n",
        encoding="utf-8",
    )
    wp = linked_mission.mission_dir / "tasks" / "WP03.md"
    wp.write_text(
        "---\nwork_package_id: WP03\nlane: in_progress\n"
        "subtasks: [T009, T010, T011]\n---\n# WP03\n",
        encoding="utf-8",
    )
    _git(linked_mission.linked, "add", ".")
    _git(linked_mission.linked, "commit", "-q", "-m", "seed mark-status acceptance")
    tasks_before = tasks_md.read_bytes()

    result = checked_cli(
        linked_mission.linked,
        "agent", "tasks", "mark-status", "T009", "T010", "T011",
        "--status", "done", "--mission", selector, "--no-auto-commit", "--json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert _payload(result)["summary"] == {"updated": 3, "already_satisfied": 0, "not_found": 0}
    assert tasks_md.read_bytes() == tasks_before
    stream = read_event_stream(linked_mission.mission_dir)
    assert len(stream.annotations) == 1
    annotation = stream.annotations[0]
    assert annotation.wp_id == "WP03"
    assert annotation.delta.subtasks == {"T009": Lane.DONE, "T010": Lane.DONE, "T011": Lane.DONE}
    _assert_primary_unchanged(linked_mission)


def test_spec_commit_never_selects_protected_primary(
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    plan = linked_mission.mission_dir / "plan.md"
    plan.write_text(plan.read_text(encoding="utf-8") + "\nLinked edit.\n", encoding="utf-8")
    result = checked_cli(linked_mission.linked, "spec-commit", str(plan), "--message",
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
    linked_mission: LinkedMission, checked_cli: Callable[..., subprocess.CompletedProcess[str]], selector: str
) -> None:
    result = checked_cli(linked_mission.linked, "agent", "mission", "check-prerequisites",
                     "--mission", selector, "--paths-only", "--json")
    assert result.returncode != 0
    assert _payload(result).get("error_code")
    _assert_primary_unchanged(linked_mission)


@pytest.mark.parametrize("selector", [None, "01M1MFE9"])
def test_multiple_missions_require_unambiguous_selection(
    linked_mission: LinkedMission,
    checked_cli: Callable[..., subprocess.CompletedProcess[str]],
    selector: str | None,
) -> None:
    _write_mission(linked_mission.linked / "kitty-specs" / "other-01M1MFE9",
                   mission_id="01M1MFE9ZZZZZZZZZZZZZZZZZZ")
    args = ["agent", "mission", "check-prerequisites", "--paths-only", "--json"]
    if selector is not None:
        args.extend(["--mission", selector])
    result = checked_cli(linked_mission.linked, *args)
    assert result.returncode != 0
    payload = _payload(result)
    assert payload.get("error_code")
    assert "feature_dir" not in payload
