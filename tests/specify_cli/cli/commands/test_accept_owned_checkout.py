"""Accept must judge and persist a mission in its explicitly owned checkout.

The primary repository deliberately contains neither the mission nor its
acceptance evidence. Real linked worktrees expose any ambient-root fold.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, NegativeInvariant
from specify_cli.cli.commands.accept import accept
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.status.emit import build_claim_policy_metadata
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_ID = "01M29ACCZTZNZDDD40BSZ7B6SH"
SLUG = "accept-owned-checkout-01m29acc"
BRANCH = "codex/owned-accept-fixture"
app = typer.Typer()
app.command()(accept)
runner = CliRunner()


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file() and ".git" not in path.relative_to(root).parts}


def _owned_mission(tmp_path: Path, *, ready: bool = True) -> tuple[Path, Path, Path]:
    primary, owned = tmp_path / "primary", tmp_path / "owned"
    (primary / ".kittify").mkdir(parents=True)
    (primary / ".kittify" / "config.yaml").write_text("mission_type_activations:\n  - software-dev\n", encoding="utf-8")
    for name in ("src", "tests", "docs"):
        (primary / name).mkdir()
        (primary / name / ".gitkeep").touch()
    _git(primary, "init", "-b", "main")
    _git(primary, "config", "user.name", "Accept tests")
    _git(primary, "config", "user.email", "accept@example.invalid")
    _git(primary, "config", "commit.gpgsign", "false")
    _git(primary, "add", ".")
    _git(primary, "commit", "-m", "Fixture project")
    _git(primary, "worktree", "add", "-b", BRANCH, str(owned))
    mission_dir = owned / "kitty-specs" / SLUG
    (mission_dir / "tasks").mkdir(parents=True)
    (mission_dir / "contracts").mkdir()
    (mission_dir / "contracts" / ".gitkeep").touch()
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": SLUG,
                "slug": SLUG,
                "mission_number": None,
                "friendly_name": "Owned acceptance fixture",
                "mission_type": "software-dev",
                "topology": "single_branch",
                "target_branch": BRANCH,
                "created_at": "2026-09-12T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for name in ("spec.md", "plan.md", "tasks.md"):
        (mission_dir / name).write_text("# Completed fixture\n\nAll work is documented.\n", encoding="utf-8")
    (mission_dir / "tasks" / "WP01-fixture.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Owned acceptance fixture\ndependencies: []\nsubtasks: []\n---\n# WP01\nFixture work.\n", encoding="utf-8"
    )
    append_event(
        mission_dir,
        StatusEvent(
            event_id="01M29ACCEPT000000000000002",
            mission_slug=SLUG,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-09-12T00:00:01Z",
            actor="test-agent",
            execution_mode="worktree",
            force=False,
            policy_metadata=build_claim_policy_metadata(
                agent="test-agent",
                shell_pid=12345,
                shell_pid_created_at="2026-09-12T00:00:00Z",
            ),
        ),
    )
    if ready:
        append_event(
            mission_dir,
            StatusEvent(
                event_id="01M29ACCEPT000000000000003",
                mission_slug=SLUG,
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.DONE,
                at="2026-09-12T00:00:02Z",
                actor="test-agent",
                execution_mode="worktree",
                force=True,
                reason="Completed test fixture",
            ),
        )
    materialize(mission_dir)
    lanes = LanesManifest(
        version=1,
        mission_slug=SLUG,
        mission_id=MISSION_ID,
        mission_branch=BRANCH,
        target_branch=BRANCH,
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01",),
                write_scope=("src/**",),
                predicted_surfaces=("test",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at="2026-09-12T00:00:03Z",
        computed_from="fixture",
    )
    (mission_dir / "lanes.json").write_text(json.dumps(lanes.to_dict()) + "\n", encoding="utf-8")
    matrix = AcceptanceMatrix(
        mission_slug=SLUG,
        criteria=[
            AcceptanceCriterion(
                criterion_id="AC1",
                description="Owned fixture meets its contract",
                proof_type="automated_test",
                pass_fail="pass",
            )
        ],
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI1",
                description="Retired symbol is absent",
                verification_method="custom_command",
                verification_command=(f'"{sys.executable}" -c "from pathlib import Path; raise SystemExit(int(Path(\'retired-owned.txt\').exists()))"'),
            )
        ],
    )
    (mission_dir / "acceptance-matrix.json").write_text(json.dumps(matrix.to_dict()) + "\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Owned mission fixture")
    (primary / "retired-owned.txt").write_text("Primary-only sentinel\n", encoding="utf-8")
    _git(primary, "add", ".")
    _git(primary, "commit", "-m", "Primary source differs from owned source")
    return primary, owned, mission_dir


@pytest.mark.parametrize("ready", [True, False])
def test_owned_diagnosis_reads_the_mission_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ready: bool,
) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path, ready=ready)
    monkeypatch.chdir(primary)
    primary_before, owned_before = _files(primary), _files(owned)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--diagnose", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["feature_dir"]) == mission_dir
    assert payload["all_done"] is ready
    assert len(payload["work_packages"]) == 1
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before


@pytest.mark.parametrize("collision", [False, True])
def test_accept_commits_only_in_the_owned_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision: bool,
) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path)
    if collision:
        shutil.copytree(mission_dir, primary / "kitty-specs" / SLUG)
        _git(primary, "add", ".")
        _git(primary, "commit", "-m", "Independent primary copy of the mission")
    monkeypatch.chdir(primary)
    primary_head, owned_head = _git(primary, "rev-parse", "HEAD"), _git(owned, "rev-parse", "HEAD")
    primary_before = _files(primary)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--mode", "local", "--actor", "tester", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["commit_created"] is True
    assert payload["accepted_by"] == "tester"
    assert Path(payload["summary"]["feature_dir"]) == mission_dir
    assert _git(owned, "rev-parse", "HEAD") != owned_head
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _files(primary) == primary_before
    assert _git(primary, "status", "--porcelain", "-uall") == ""
    assert _git(owned, "status", "--porcelain", "-uall") == ""
    committed = json.loads(_git(owned, "show", f"HEAD:kitty-specs/{SLUG}/meta.json"))
    assert committed["accepted_by"] == "tester"
    matrix = json.loads(_git(owned, "show", f"HEAD:kitty-specs/{SLUG}/acceptance-matrix.json"))
    assert matrix["negative_invariants"][0]["result"] == "confirmed_absent"


def test_accept_checks_the_owned_source_invariant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path)
    (owned / "retired-owned.txt").write_text("Forbidden in this fixture\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Violate the source invariant")
    monkeypatch.chdir(primary)
    metadata_before = (mission_dir / "meta.json").read_bytes()
    primary_before = _files(primary)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["ok"] is False
    matrix = json.loads((mission_dir / "acceptance-matrix.json").read_text(encoding="utf-8"))
    assert matrix["negative_invariants"][0]["result"] == "still_present"
    assert (mission_dir / "meta.json").read_bytes() == metadata_before
    assert _files(primary) == primary_before


def test_unfinished_owned_mission_cannot_be_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path, ready=False)
    monkeypatch.chdir(primary)
    meta_before = (mission_dir / "meta.json").read_bytes()
    primary_before = _files(primary)
    head_before = _git(owned, "rev-parse", "HEAD")
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["all_done"] is False
    assert (mission_dir / "meta.json").read_bytes() == meta_before
    assert _git(owned, "rev-parse", "HEAD") == head_before
    assert _files(primary) == primary_before


def test_without_declaration_owned_mission_remains_invisible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, _ = _owned_mission(tmp_path)
    monkeypatch.chdir(primary)
    primary_before, owned_before = _files(primary), _files(owned)
    result = runner.invoke(app, ["--mission", SLUG, "--diagnose", "--json"])
    assert result.exit_code != 0
    assert json.loads(result.output)["error"] == "mission_not_found"
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before


def test_foreign_checkout_is_refused_before_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, _ = _owned_mission(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _git(foreign, "init", "-b", "unrelated")
    monkeypatch.chdir(primary)
    primary_before, owned_before, foreign_before = _files(primary), _files(owned), _files(foreign)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(foreign), "--json"])
    assert result.exit_code == 1, result.output
    assert "error_code" in json.loads(result.output)
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before
    assert _files(foreign) == foreign_before


@pytest.mark.parametrize("dirty_file", ["spec.md", "issue-matrix.md"])
def test_owned_dirty_file_is_not_sibling_coordination_residue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dirty_file: str) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path)
    primary_mission = primary / "kitty-specs" / SLUG
    shutil.copytree(mission_dir, primary_mission)
    meta = json.loads((primary_mission / "meta.json").read_text(encoding="utf-8"))
    meta.update(topology="coord", coordination_branch="kitty/primary-coordination")
    (primary_mission / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _git(primary, "add", ".")
    _git(primary, "commit", "-m", "Primary copy has different topology")
    _git(primary, "branch", "kitty/primary-coordination")
    (mission_dir / dirty_file).write_text("# Uncommitted requirement change\n", encoding="utf-8")
    monkeypatch.chdir(primary)
    primary_before = _files(primary)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    assert any(dirty_file in path for path in json.loads(result.output)["git_dirty"])
    assert _files(primary) == primary_before


def test_protected_target_is_refused_before_matrix_or_metadata_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path)
    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    meta["target_branch"] = "main"
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Protected target fixture")
    monkeypatch.chdir(primary)
    primary_before, owned_before = _files(primary), _files(owned)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    assert "non-protected target branch" in json.loads(result.output)["error"]
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before


def test_ownership_does_not_extend_to_a_coordination_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.coordination.workspace import CoordinationWorkspace
    from specify_cli.missions._read_path_resolver import coord_feature_dir

    primary, owned, mission_dir = _owned_mission(tmp_path)
    mid8 = MISSION_ID[:8]
    coord_branch = CoordinationWorkspace.branch_name(SLUG, mid8)
    coord_root = CoordinationWorkspace.worktree_path(owned, SLUG, mid8)
    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(topology="coord", coordination_branch=coord_branch)
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (owned / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    _git(owned, "add", ".")
    _git(owned, "commit", "-m", "Coordination surface requires another checkout")
    _git(primary, "worktree", "add", "-b", coord_branch, str(coord_root), BRANCH)
    # Coordination uses the declared (uppercase) identity suffix, including
    # when the primary mission directory carries a lowercase legacy suffix.
    coord_mission = coord_feature_dir(owned, SLUG, mid8)
    if not coord_mission.exists():
        shutil.copytree(mission_dir, coord_mission)
    monkeypatch.chdir(primary)
    primary_before, owned_before = _files(primary), _files(owned)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert "error" in payload, result.output
    assert "outside the owned checkout" in payload["error"]
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before


@pytest.mark.parametrize("failure", ["error", "verification", "exception"])
def test_failed_owned_cutover_cannot_record_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from specify_cli.migration import runtime_state_cutover as cutover
    from specify_cli.migration.backfill_runtime_state import VerifyResult

    primary, owned, mission_dir = _owned_mission(tmp_path)
    monkeypatch.chdir(primary)
    primary_before = _files(primary)
    metadata_before = (mission_dir / "meta.json").read_bytes()
    head_before = _git(owned, "rev-parse", "HEAD")

    def refuse(feature_dir: Path, **kwargs: object) -> cutover.CutoverResult:
        assert feature_dir == mission_dir
        assert kwargs["effective_root"] == owned
        if failure == "exception":
            raise RuntimeError("Injected cutover failure")
        return cutover.CutoverResult(
            slug=SLUG,
            flipped=False,
            error="Injected cutover refusal" if failure == "error" else None,
            verify=VerifyResult(ok=False, wp_count=1, mismatches=("missing seed",)),
        )

    monkeypatch.setattr(cutover, "stamp_accept_cutover", refuse)
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 1, result.output
    assert "cutover" in json.loads(result.output)["error"].lower()
    assert (mission_dir / "meta.json").read_bytes() == metadata_before
    assert _git(owned, "rev-parse", "HEAD") == head_before
    assert _files(primary) == primary_before


def test_published_primary_copy_does_not_change_owned_placement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    primary, owned, mission_dir = _owned_mission(tmp_path)
    primary_mission = primary / "kitty-specs" / SLUG
    shutil.copytree(mission_dir, primary_mission)
    meta = json.loads((primary_mission / "meta.json").read_text(encoding="utf-8"))
    meta.update(baseline_merge_commit=_git(primary, "rev-parse", "HEAD"), mission_number=42, target_branch="retired-mission")
    (primary_mission / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _git(primary, "add", ".")
    _git(primary, "commit", "-m", "Published primary copy")
    monkeypatch.chdir(primary)
    primary_before = _files(primary)
    primary_head = _git(primary, "rev-parse", "HEAD")
    result = runner.invoke(app, ["--mission", SLUG, "--owned-checkout", str(owned), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["commit_created"] is True
    assert _files(primary) == primary_before
    assert _git(primary, "rev-parse", "HEAD") == primary_head
    assert _git(owned, "status", "--porcelain") == ""


@pytest.mark.parametrize("target, expected", [(BRANCH, "consolidated"), ("retired-owned-mission", "published"), (None, "consolidated")])
def test_owned_lifecycle_reads_its_own_durable_evidence(tmp_path: Path, target: str | None, expected: str) -> None:
    from mission_runtime.lifecycle_phase import resolve_lifecycle_phase

    primary, owned, mission_dir = _owned_mission(tmp_path)
    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(baseline_merge_commit=_git(owned, "rev-parse", "HEAD"), mission_number=42, target_branch=target)
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    primary_before = _files(primary)
    assert resolve_lifecycle_phase(SLUG, primary, effective_root=owned).value == expected
    assert _files(primary) == primary_before


@pytest.mark.parametrize("field", ["repo_root", "feature_dir"])
def test_owned_summary_cannot_be_rebound_before_persistence(tmp_path: Path, field: str) -> None:
    from specify_cli.acceptance import AcceptanceError, collect_feature_summary, perform_acceptance

    primary, owned, mission_dir = _owned_mission(tmp_path)
    summary = collect_feature_summary(owned, SLUG, effective_root=owned)
    setattr(summary, field, primary if field == "repo_root" else primary / "kitty-specs" / SLUG)
    primary_before, owned_before = _files(primary), _files(owned)
    with pytest.raises(AcceptanceError, match="no longer identifies"):
        perform_acceptance(summary, mode="local", actor="test-actor", auto_commit=True)
    assert _files(primary) == primary_before
    assert _files(owned) == owned_before
