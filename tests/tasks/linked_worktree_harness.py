"""Real-Git Mission fixture and primary-checkout guard for planning acceptance."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tests.utils import write_wp

MISSION_SLUG = "linked-worktree-prerequisite-resolution-01M1MFE9"
MISSION_ID = "01M1MFE98JDK0S33WSYBQRPSDF"
TASK_BRANCH = "codex/task"


def git(repo: Path, *args: str) -> str:
    """Run real Git without allowing read-only probes to refresh the index."""
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, timeout=30,
    ).stdout.strip()


@dataclass(frozen=True)
class PrimarySnapshot:
    """Stable checkout state; shared worktree objects/refs are intentionally excluded."""

    head: str
    branch: str
    status: str
    index: bytes
    files: tuple[tuple[str, bytes], ...]


def snapshot_primary(primary: Path) -> PrimarySnapshot:
    """Capture tracked, untracked and ignored file bytes plus the actual Git index."""
    index = Path(git(primary, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    files: list[tuple[str, bytes]] = []
    for directory, dirs, names in os.walk(primary):
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in sorted(names):
            path = Path(directory) / name
            if path == primary / ".git":
                continue
            content = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
            files.append((path.relative_to(primary).as_posix(), content))
    return PrimarySnapshot(
        head=git(primary, "rev-parse", "HEAD"),
        branch=git(primary, "symbolic-ref", "HEAD"),
        status=git(primary, "status", "--porcelain=v1", "--untracked-files=all"),
        index=index.read_bytes(), files=tuple(sorted(files)),
    )


@dataclass(frozen=True)
class LinkedMission:
    """A registered secondary checkout; no production resolver is an assertion oracle."""

    primary: Path
    linked: Path
    mission_dir: Path

    def run(
        self, cwd: Path, *args: str, env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Capture a command's real result and always reject primary mutations."""
        before = snapshot_primary(self.primary)
        try:
            return subprocess.run(
                args, cwd=cwd, capture_output=True, text=True, check=False,
                env=env, timeout=60,
            )
        finally:
            assert snapshot_primary(self.primary) == before, "Command mutated the primary checkout"


def write_mission(mission_dir: Path, mission_id: str = MISSION_ID) -> None:
    """Seed substantive planning inputs and canonical planned-WP state in a fixture."""
    for child in ("tasks", "checklists", "research", "contracts"):
        (mission_dir / child).mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": mission_dir.name,
                    "slug": mission_dir.name, "mission_type": "software-dev",
                    "target_branch": TASK_BRANCH}), encoding="utf-8",
    )
    (mission_dir / "spec.md").write_text(
        "# Linked Mission\n\n## Functional Requirements\n\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n| --- | --- | --- | --- |\n"
        "| FR-001 | Resolve this Mission. | Planning selects the owned checkout. | proposed |\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text(
        "# Implementation Plan\n\n## Technical Context\n\n**Language/Version**: Python 3.12\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text("# Tasks\n\n- [ ] T001 Verify selected Mission.\n", encoding="utf-8")
    write_wp(mission_dir.parent.parent, mission_dir.name, "planned", "WP01")


def create_linked_mission(directory: Path) -> LinkedMission:
    """Create an isolated primary and registered task worktree under a fresh temp path."""
    primary = directory / "repo"
    primary.mkdir()
    git(primary, "init", "-q", "-b", "main")
    for key, value in (("user.email", "test@example.invalid"), ("user.name", "Test"),
                       ("core.autocrlf", "false"), ("core.longpaths", "true")):
        git(primary, "config", key, value)
    (primary / "README.md").write_text("seed\n", encoding="utf-8")
    (primary / ".gitignore").write_text(".kittify/sync-state.json\n", encoding="utf-8")
    templates = primary / ".kittify" / "templates"
    templates.mkdir(parents=True)
    (templates.parent / "config.yaml").write_text("project:\n  name: linked-test\n", encoding="utf-8")
    (templates / "plan-template.md").write_text("# Implementation Plan\n", encoding="utf-8")
    git(primary, "add", ".")
    git(primary, "commit", "-q", "-m", "seed primary")
    linked = directory / "linked"
    git(primary, "worktree", "add", "-q", "-b", TASK_BRANCH, str(linked), "main")
    mission_dir = linked / "kitty-specs" / MISSION_SLUG
    write_mission(mission_dir)
    git(linked, "add", ".")
    git(linked, "commit", "-q", "-m", "seed linked Mission")
    return LinkedMission(primary, linked, mission_dir)
