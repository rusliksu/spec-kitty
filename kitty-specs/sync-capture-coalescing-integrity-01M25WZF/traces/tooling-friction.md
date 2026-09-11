# Tooling friction: owned-worktree mission resolution for task/status commands

Mission: `sync-capture-coalescing-integrity-01M25WZF`
Recorded: 2026-09-11

## What fails

From the owned linked worktree
`C:\Users\Ruslan\.codex-worktrees\spec-kitty-sync-capture-coalescing` (branch
`codex/sync-capture-coalescing`), on `main` `78c1e9ab1`:

```text
spec-kitty agent tasks move-task WP01 --to doing --mission sync-capture-coalescing-integrity-01M25WZF --agent codex --assignee codex --json
  -> {"error": "mission_not_found", "handle": "sync-capture-coalescing-integrity-01M25WZF"}

spec-kitty agent status lifecycle --mission <slug> --json   -> mission_not_found
spec-kitty agent status lifecycle --mission 01M25WZF --json -> mission_not_found
spec-kitty agent status lifecycle --mission 01M25WZFGH0W3EA3F8C17WQ4QD --json -> mission_not_found
spec-kitty agent status validate  --mission <slug> --json   -> mission_not_found

SPECIFY_REPO_ROOT=<owned worktree> spec-kitty agent status lifecycle --mission <slug> --json
  -> mission_not_found   (the override resolves through get_main_repo_root, which
     collapses the linked worktree back to the primary checkout)

spec-kitty tasks --mission <slug> --json
  -> FEATURE_CONTEXT_UNRESOLVED: "443 missions found, pass --mission <slug> to disambiguate"

spec-kitty agent tasks finalize-tasks --mission <slug> --json -> mission_not_found
```

## What works

```text
spec-kitty next --mission <slug> --owned-checkout <worktree> --json         -> ok
spec-kitty spec-commit <file> --mission <slug> --owned-checkout <wt> -m ..  -> ok
spec-kitty agent mission create --owned-checkout <worktree> ...             -> ok
```

Also observed: `spec-kitty research` has no `--owned-checkout` seam and wrote its four scaffold
files into the **protected primary checkout**; they were moved into the mission worktree and the
primary was cleaned.

## Impact on this mission

- Planning pipeline: `tasks.md` and the WP frontmatter bootstrap were produced by hand using the
  same rules the CLI applies (`_apply_bootstrap_fields` / `generate_tasks_md_from_manifest`),
  because `finalize-tasks` could not see the mission.
- Review surface: no lane transition and no `review_result` event could be emitted; WP01/WP02
  approvals are recorded as a reviewed verdict in `traces/wp-review-verdicts.md` instead.
- The mission runtime therefore stops at `implement` with `reason: "no actionable wp"`.

## Remediation paths

1. Land pull request 20 (mission `linked-worktree-prerequisite-resolution-01M1MFE9`): it carries
   the owned-mission routing for `move-task` (`tasks_move_context.py`) and the
   `tests/tasks/test_move_task_owned_checkout.py` suite that proves it.
2. Give the `agent tasks` and `agent status` command families the same `--owned-checkout` seam
   that `next`, `spec-commit` and `agent mission create` already accept.
3. Bonus: let the runtime's op bookkeeping either exclude the frozen
   `kitty-ops/lifecycle.jsonl` or avoid committing it on feature branches; this mission had to
   restore that file twice to keep the byte-frozen-archive gate green.
