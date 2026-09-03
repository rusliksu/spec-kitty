# Tooling Friction Trace

- 2026-09-03: Installed Spec Kitty correctly re-anchors arbitrary linked
  worktrees to the repository root checkout for planning. That conflicts with
  this task's stricter external task-worktree policy, so the mission baseline
  is recorded directly in the task branch rather than mutating the primary
  checkout. All CLI probes use an isolated temporary user profile.
