# Tooling Friction Trace

- 2026-09-03: Installed Spec Kitty correctly re-anchors arbitrary linked
  worktrees to the repository root checkout for planning. That conflicts with
  this task's stricter external task-worktree policy, so the mission baseline
  is recorded directly in the task branch rather than mutating the primary
  checkout. All CLI probes use an isolated temporary user profile.
- 2026-09-03: The repository pytest startup takes roughly 75–120 seconds even
  for two files; no retry-to-green was used, and each run was allowed to finish.
- 2026-09-03: `spec-kitty --version` is an eager Typer option and exits before
  startup bootstrap. The valid candidate smoke uses
  `spec-kitty upgrade --agent-check --json`, which traverses the callback.
- 2026-09-03: An exploratory full `tests/specify_cli/skills` run exposed nine
  unrelated pre-existing failures (Windows path separators/read-only deletion
  plus one command-renderer expectation). No matching open GitHub issue was
  found. Charter requires an issue before accepting that baseline, but creating
  a public issue is outside the current authorization; closeout remains gated.
