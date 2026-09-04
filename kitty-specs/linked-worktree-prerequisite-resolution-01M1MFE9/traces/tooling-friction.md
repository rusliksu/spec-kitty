# Tooling Friction Trace

- Mission creation with explicit `--owned-checkout` succeeded on the fresh task worktree; Windows origin binding emitted the separately tracked missing-`fcntl` warning.
- `spec-commit` incorrectly resolved protected primary `main`, so the substantive spec was committed explicitly on the validated task branch.
- `decision verify` and `decision open` could not resolve the task-worktree-only Mission; the confirmed scope is recorded in the spec and Bead `spk-1m6` rather than an unavailable decision artifact.
- `setup-plan` returned `PLAN_CONTEXT_UNRESOLVED` after action-context resolution succeeded. Planning artifacts were therefore authored in the validated Mission directory without bypassing runtime implementation or merge guards.
- No primary files, active CLI installation, release, deployment, push, or PR were changed during planning.

## 2026-09-04 — Post-analysis workspace lookup recovery

- Analysis is now ready and fresh at report commit `d969af388`. The real
  `agent action implement WP01 --mission linked-worktree-prerequisite-resolution-01M1MFE9 --agent codex`
  progressed past analysis but looked for WP01 under the primary checkout.
- `workflow.implement` passed the validated `effective_root` through earlier
  preflights but omitted it at the write-intent workspace resolver call. The
  resolver already supports that anchor and returns the expected lane with
  checkout-identity enforcement intact. No new resolution authority is needed.
- Approved lifecycle bootstrap recovery: RED commit `f9c56faef` adds real-CLI
  slug/ID tests that must reach the owned missing-manifest guard after fresh
  analysis. Both failed on primary-only WP lookup, then passed after forwarding
  existing `anchor_options`. Existing product assertions were not changed.
- The initial test-fixture attempt lacked its planned status event and stopped
  at the status guard; that setup error is not counted as product RED evidence.
- Verification: 2 targeted real-CLI tests passed; 43 single-resolution,
  workflow and checkout-identity regressions passed; Ruff, strict mypy on five
  explicit inputs, compileall and diff-check passed. Temporary test repositories
  used unique `C:/Windows/Temp/spk-workspace-*` basetemps.
- This is bootstrap recovery, not the WP01 harness deliverable or approval.
  Allocation/claim and subsequent lifecycle consumers still require live proof.
- Live canary on fix commit `9ad2345e0` passed the repaired lookup and reached
  `ensure_workspace_materialized`'s blanket worktree-creation refusal:
  `Workspace does not exist and cannot be created from a worktree.` This guard
  was not removed or bypassed. The suggested primary invocation is not a valid
  workaround for a Mission whose planning artifacts exist only in the owned
  task checkout. A follow-up needs a governed owned-planning-checkout allocation
  contract, preserving foreign-checkout, husk, ancestry and identity safeguards.
- Live postconditions: lane-a path absent; task and primary checkouts clean;
  primary HEAD `6befd9b43174b9f2c117f8bc02443001c9c25cb6` unchanged; status event
  SHA256 `0BA37C340B47384093A1A6C29A3B674446BAA5DC72460294711DA6C93E2D5FDF`
  unchanged. WP01 harness implementation has not started.
