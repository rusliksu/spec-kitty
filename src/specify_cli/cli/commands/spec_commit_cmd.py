"""Mission-aware ``spec-commit`` entrypoint (FR-001/002/003).

Closes the #1619 P0 specify-phase deadlock: unlike the generic ``safe-commit``
command (which is mission-blind), this command derives the mission slug from a
``kitty-specs/<slug>/`` path argument or ``--mission``, resolves the
:class:`~specify_cli.git.protection_policy.ProtectionPolicy` at the command
boundary, and routes the commit through
:func:`~specify_cli.coordination.commit_router.commit_for_mission`.

Planning artifacts commit directly to the Mission's planning branch, never
through coordination. Protected-primary writes are refused. An explicitly
selected caller-owned Mission keeps its artifact paths and committing checkout,
while protection policy remains anchored at the canonical repository root.

Design basis: WP02 / IC-02 / ADR ``2026-06-21-1``.

C-001: reuses the canonical materialiser, no new materialiser.
#1718: materialisation happens at this commit boundary, not at read time.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from specify_cli.cli.console import console

from mission_runtime import ActionContextError, MissionArtifactKind, mission_context_for
from specify_cli.coordination.commit_router import CommitRouterResult, commit_for_mission
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.task_utils import find_repo_root
from specify_cli.missions.operation_context import MissionOperationContext, resolve_mission_operation_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_repo_root() -> Path:
    """Return the primary repo root (follows worktree links to main checkout)."""
    root: Path = find_repo_root()
    return root


def _derive_mission_slug(path_arg: str | None, mission_opt: str | None) -> str | None:
    """Derive the mission slug from a ``kitty-specs/<slug>/`` path or ``--mission``."""
    if mission_opt:
        return mission_opt.strip()
    if path_arg:
        # Accept either the slug directly or a ``kitty-specs/<slug>`` path.
        p = Path(path_arg)
        # If the path contains a ``kitty-specs`` component, take the part after it.
        parts = p.parts
        try:
            idx = next(i for i, part in enumerate(parts) if part == KITTY_SPECS_DIR)
            # slug is the component immediately after ``kitty-specs``
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except StopIteration:
            pass
        # Otherwise treat the final component as the slug.
        return p.name or None
    return None


def _normalize_commit_files(
    files: list[Path], operation: MissionOperationContext, mission_slug: str,
) -> tuple[Path, ...]:
    """Interpret selected-Mission paths and refuse resolved escapes before staging."""
    if operation.mission_anchor_root == operation.repository_root:
        return tuple((operation.repository_root / file).resolve() for file in files)
    context = mission_context_for(
        operation.repository_root, mission_slug, effective_root=operation.mission_anchor_root,
    )
    mission_dir = context.artifact(MissionArtifactKind.SPEC).write_dir.resolve()
    resolved_files: list[Path] = []
    for file in files:
        if file.is_absolute():
            resolved = file.resolve()
        elif file.parts and file.parts[0] == KITTY_SPECS_DIR:
            resolved = (operation.mission_anchor_root / file).resolve()
        else:
            resolved = (mission_dir / file).resolve()
        if not resolved.is_relative_to(mission_dir):
            raise ValueError(f"Artifact outside selected Mission: {file}")
        resolved_files.append(resolved)
    return tuple(resolved_files)


def _payload(
    *,
    success: bool,
    committed: bool = False,
    placement_ref: str | None = None,
    commit_hash: str | None = None,
    error: str | None = None,
    diagnostic: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "result": "success" if success else "error",
        "success": success,
        "committed": committed,
    }
    if placement_ref is not None:
        result["placement_ref"] = placement_ref
    if commit_hash is not None:
        result["commit_hash"] = commit_hash
    if error is not None:
        result["error"] = error
    if diagnostic is not None:
        result["diagnostic"] = diagnostic
    return result


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def spec_commit_command(
    files: list[Path] = typer.Argument(
        ...,
        help=(
            "Spec artifacts to commit (absolute or relative paths). "
            "Must belong to the mission resolved via --mission or the "
            "kitty-specs/<slug>/ path."
        ),
    ),
    message: str = typer.Option(..., "--message", "-m", help="Commit message."),
    mission: str | None = typer.Option(
        None,
        "--mission",
        help=(
            "Mission slug (e.g. '001-my-mission'). When omitted, the slug is "
            "derived from the first file argument's kitty-specs/<slug>/ path."
        ),
    ),
    target_branch: str | None = typer.Option(
        None,
        "--target-branch",
        help=(
            "Short primary branch name used for the post-commit ff-advance "
            "(WP09 / FR-010). Optional."
        ),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Commit spec artifacts to the mission's resolved placement.

    Planning writes use the Mission's direct planning surface. A protected
    destination is refused; coordination is not a bypass for that protection.
    """
    try:
        repo_root = _current_repo_root()

        # Derive mission slug.
        first_path_arg = str(files[0]) if files else None
        mission_slug = _derive_mission_slug(first_path_arg, mission)
        if not mission_slug:
            _err(
                json_output,
                "Cannot resolve mission slug. Pass --mission <slug> or provide a "
                "kitty-specs/<slug>/ path as the first argument.",
            )
            raise typer.Exit(1)

        operation = resolve_mission_operation_context(repo_root, mission_slug, cwd=Path.cwd())
        owned = operation.mission_anchor_root != operation.repository_root
        if operation.identity is not None:
            mission_slug = operation.identity.mission_slug
        abs_files = _normalize_commit_files(files, operation, mission_slug)

        # Boundary-resolve the protection policy (FR-007, NFR-003).
        policy = ProtectionPolicy.resolve(repo_root)

        result: CommitRouterResult = commit_for_mission(
            repo_root=repo_root,
            mission_slug=mission_slug,
            files=abs_files,
            message=message,
            policy=policy,
            # The operator-facing ``spec-commit`` entry point commits the SPEC
            # planning artifact (write-surface-coherence WP02 / T007). SPEC is a
            # primary kind, so it lands on the primary target branch for every
            # topology — no planning→coord transit.
            kind=MissionArtifactKind.SPEC,
            target_branch=target_branch,
            **({"operation": operation} if owned else {}),
        )

        if result.status == "committed":
            payload = _payload(
                success=True,
                committed=True,
                placement_ref=result.placement_ref,
                commit_hash=result.commit_hash,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(
                    f"[green]✓[/green] Spec artifact(s) committed to {result.placement_ref}"
                )
                if result.commit_hash:
                    console.print(f"[dim]Commit: {result.commit_hash[:7]}[/dim]")

        elif result.status == "unchanged":
            payload = _payload(success=True, committed=False, placement_ref=result.placement_ref)
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print("[dim]Spec artifact(s) unchanged, no commit needed[/dim]")

        elif result.status == "no_op_wrong_surface":
            # T008: actionable refusal — tell the operator what happened and how to recover.
            recovery_cmd = (
                f"spec-kitty spec-commit --mission {mission_slug} "
                f"-m '{message}' <files>"
            )
            diag = result.diagnostic or "Artifact absent at resolved placement."
            actionable = (
                f"{diag}\n"
                f"After correcting the branch or artifact location above, retry:\n"
                f"  {recovery_cmd}"
            )
            payload = _payload(
                success=False,
                error=actionable,
                placement_ref=result.placement_ref,
                diagnostic=result.diagnostic,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(f"[red]Error:[/red] {actionable}")
            raise typer.Exit(1)

        else:  # "error"
            payload = _payload(
                success=False,
                error=result.diagnostic or "Commit failed.",
                placement_ref=result.placement_ref,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(f"[red]Error:[/red] {result.diagnostic or 'Commit failed.'}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except (ActionContextError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        payload = _payload(success=False, error=str(exc))
        if json_output:
            print(json.dumps(payload, indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


def _err(json_output: bool, message: str) -> None:
    if json_output:
        print(json.dumps(_payload(success=False, error=message), indent=2))
    else:
        console.print(f"[red]Error:[/red] {message}")
