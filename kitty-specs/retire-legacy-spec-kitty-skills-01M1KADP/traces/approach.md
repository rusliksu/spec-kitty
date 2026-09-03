# Approach Trace

- 2026-09-03: Prefer the existing retirement authority plus default registry
  filtering. Keep legacy source assets in the package for reference/migration
  compatibility; make them non-installable through the canonical registry.
- 2026-09-03: One coupled WP is smaller and safer than separate test/policy WPs;
  ATDD still receives its own first commit.
- 2026-09-03: RED was captured as an import failure for the missing mapping;
  after the mapping and registry filter, the focused surface passed 19 tests.
- 2026-09-03: Existing Windows tests now patch `Path.home()` directly instead
  of setting POSIX-only `HOME`, keeping global-root fixtures deterministic.
- 2026-09-03: Focused migration surface is green: 37 passed. Ruff and mypy are
  green on the changed policy, registry, bootstrap, and test files.
- 2026-09-03: Built wheel registry reports 41 discovered skills, zero retired
  aliases, and all 14 canonical replacements.
- 2026-09-03: Three independent adversarial reviewers converged on a blocker:
  prefix-wide cleanup could delete an unregistered user-authored
  `spec-kitty-*` skill. A behavioral RED reproduced the deletion.
- 2026-09-03: Cleanup now uses only the finite retired-name authority. The
  regression preserves unknown prefixed skills, and current-lock coverage runs
  against both installable global roots.
- 2026-09-03: Rebuilt and installed the superseding wheel from implementation
  commit `30e790867`; isolated and real-profile startup checks are green.
- 2026-09-03: Fork CI portability uses a repository-name conditional rather
  than replacing upstream runner policy: upstream keeps Blacksmith, forks use
  GitHub-hosted Linux or Windows runners. Scope is the twelve direct and
  reusable workflows reachable from the current draft PR; unrelated
  release-only and scheduled workflows remain unchanged.
- 2026-09-03: Fork `CI Quality` also uses a fork-specific concurrency namespace
  because one obsolete no-job run remained queued after cancellation. Upstream
  keeps its exact existing concurrency key and cancellation semantics.
