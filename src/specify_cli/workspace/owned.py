"""Git evidence for reviewing an explicitly owned single-branch workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from specify_cli.core.git_ops import resolve_primary_branch
from specify_cli.task_utils import run_git


@dataclass(frozen=True)
class ImplementationRange:
    base_commit: str
    head_commit: str
    upstream_ref: str


def resolve_implementation_range(checkout: Path, primary_root: Path, target_branch: str) -> ImplementationRange:
    """Pin the configured primary upstream and HEAD; refuse unproven history."""
    from specify_cli.workspace.context import WorkspaceResolutionError, verify_workspace_toplevel

    def refuse(check: str, detail: str) -> NoReturn:
        raise WorkspaceResolutionError(workspace_path=checkout, failed_check=check, detail=detail)

    if not (checkout / ".git").exists():
        refuse("owned-checkout", "The declared checkout has no .git entry.")
    top_error = verify_workspace_toplevel(checkout)
    if top_error is not None:
        raise top_error
    branch = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=checkout, check=False)
    if branch.returncode != 0 or branch.stdout.strip() != target_branch:
        refuse("target-branch", f"The checkout must be attached to the mission target {target_branch!r}.")

    primary_branch = str(resolve_primary_branch(primary_root, bias=False))
    if primary_branch == target_branch:
        refuse("implementation-base", "The primary branch must be distinct from the mission target branch.")
    upstream = run_git(["rev-parse", "--symbolic-full-name", f"{primary_branch}@{{upstream}}"], cwd=primary_root, check=False)
    if upstream.returncode != 0 or not upstream.stdout.strip():
        refuse("implementation-base", f"Configure an upstream for the primary branch {primary_branch!r}; no historical base is inferred.")
    upstream_ref = upstream.stdout.strip()
    base = run_git(["rev-parse", "--verify", f"{upstream_ref}^{{commit}}"], cwd=checkout, check=False)
    head = run_git(["rev-parse", "--verify", "HEAD^{commit}"], cwd=checkout, check=False)
    if base.returncode != 0 or head.returncode != 0:
        refuse("implementation-base", "The primary upstream and checkout HEAD must resolve to commits.")
    base_commit, head_commit = base.stdout.strip(), head.stdout.strip()
    bases = run_git(["merge-base", "--all", head_commit, base_commit], cwd=checkout, check=False)
    if bases.returncode != 0 or bases.stdout.splitlines() != [base_commit]:
        refuse("implementation-base", "The configured primary upstream must be an ancestor of this checkout; update the task branch before review.")
    return ImplementationRange(base_commit, head_commit, upstream_ref)


def has_owned_implementation_changes(checkout: Path, base: str, head: str, owned_files: list[str]) -> bool:
    """Require delivered changes in this WP's authored scope, excluding bookkeeping."""
    if not owned_files:
        return False
    result = run_git(
        ["diff", "--name-only", base, head, "--", *owned_files, ":(exclude)kitty-specs/**", ":(exclude).kittify/**", ":(exclude)kitty-ops/**"],
        cwd=checkout,
        check=True,
    )
    return bool(result.stdout.strip())


def verify_review_head(checkout: Path, branch: str, head_commit: str) -> None:
    """Refuse a checkout changed after its review evidence was resolved."""
    from specify_cli.workspace.context import WorkspaceResolutionError

    actual_branch = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=checkout, check=False)
    actual_head = run_git(["rev-parse", "HEAD"], cwd=checkout, check=False)
    if actual_branch.returncode != 0 or actual_head.returncode != 0 or actual_branch.stdout.strip() != branch or actual_head.stdout.strip() != head_commit:
        raise WorkspaceResolutionError(
            workspace_path=checkout, failed_check="review-head-changed", detail="The checkout branch or HEAD changed during review; rerun the checks."
        )
