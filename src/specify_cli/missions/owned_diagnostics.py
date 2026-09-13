"""Read-only diagnostics after a command validates an explicit checkout claim."""

from pathlib import Path

from specify_cli.core.paths import assert_safe_path_segment, get_main_repo_root


def mission_divergence_warning(owned_root: Path, mission_slug: str) -> str | None:
    """Report two different mission copies; never select or reconcile their bytes."""
    from mission_runtime import MissionArtifactKind, placement_seam

    assert_safe_path_segment(mission_slug)
    primary = get_main_repo_root(owned_root)
    if primary.resolve() == owned_root.resolve():
        return None
    declared_dir = placement_seam(owned_root, mission_slug, effective_root=owned_root).read_dir(MissionArtifactKind.PRIMARY_METADATA)
    primary_dir = placement_seam(primary, mission_slug).read_dir(MissionArtifactKind.PRIMARY_METADATA)
    if not declared_dir.is_dir() or not primary_dir.is_dir():
        return None

    def files(directory: Path) -> dict[Path, Path]:
        return {path.relative_to(directory): path for path in directory.rglob("*") if path.is_file() and not path.is_symlink()}

    declared_files, primary_files = files(declared_dir), files(primary_dir)
    if declared_files.keys() == primary_files.keys() and all(
        path.read_bytes() == primary_files[relative].read_bytes() for relative, path in declared_files.items()
    ):
        return None
    return (
        f"owned_mission_divergence: mission {mission_slug!r} differs between the primary and declared checkout. "
        "The declared checkout is authoritative for this command; the primary is unchanged."
    )


def warn_owned_mission_divergence(owned_root: Path, mission_slug: str) -> None:
    """Keep diagnostics on stderr so machine-readable command output stays valid."""
    import typer

    message = mission_divergence_warning(owned_root, mission_slug)
    if message is not None:
        typer.echo(message, err=True)
