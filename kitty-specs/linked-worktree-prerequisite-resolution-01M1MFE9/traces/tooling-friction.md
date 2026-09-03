# Tooling Friction Trace

- Mission creation with explicit `--owned-checkout` succeeded on the fresh task worktree; Windows origin binding emitted the separately tracked missing-`fcntl` warning.
- `spec-commit` incorrectly resolved protected primary `main`, so the substantive spec was committed explicitly on the validated task branch.
- `decision verify` and `decision open` could not resolve the task-worktree-only Mission; the confirmed scope is recorded in the spec and Bead `spk-1m6` rather than an unavailable decision artifact.
- `setup-plan` returned `PLAN_CONTEXT_UNRESOLVED` after action-context resolution succeeded. Planning artifacts were therefore authored in the validated Mission directory without bypassing runtime implementation or merge guards.
- No primary files, active CLI installation, release, deployment, push, or PR were changed during planning.
