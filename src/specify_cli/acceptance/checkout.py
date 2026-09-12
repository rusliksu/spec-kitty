"""Keep explicitly owned acceptance work inside its declared checkout."""

from __future__ import annotations

from pathlib import Path

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.task_utils import run_git


def validate_owned_acceptance_scope(
    repo_root: Path,
    mission_slug: str,
    *,
    commit_required: bool,
    feature_dir: Path | None = None,
) -> None:
    """Validate real placements before any owned acceptance mutation.

    Ownership of one checkout does not authorize a second coordination
    checkout or a protected target. Topology and branch policy stay owned
    by the existing placement and protection authorities.
    """
    from specify_cli.acceptance import AcceptanceError

    seam = placement_seam(repo_root, mission_slug, effective_root=repo_root)
    for kind in (
        MissionArtifactKind.PRIMARY_METADATA,
        MissionArtifactKind.STATUS_STATE,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
    ):
        surface = seam.read_dir(kind).resolve()
        if surface.parent.parent != repo_root.resolve():
            raise AcceptanceError(f"Acceptance surface {surface} is outside the owned checkout {repo_root}")
        if kind is MissionArtifactKind.PRIMARY_METADATA and feature_dir is not None and feature_dir.resolve() != surface:
            raise AcceptanceError("Acceptance summary no longer identifies the owned mission surface")
    if commit_required:
        branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True).stdout.strip()
        target = seam.write_target(MissionArtifactKind.PRIMARY_METADATA)
        if branch != target.ref or ProtectionPolicy.resolve(repo_root).is_protected(target.ref):
            raise AcceptanceError(f"Owned acceptance requires the non-protected target branch {target.ref!r} to be checked out; current branch is {branch!r}")
