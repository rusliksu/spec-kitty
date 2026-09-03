# Verification Evidence

## RED

Command:

```text
python -m pytest tests/specify_cli/skills/test_registry.py tests/runtime/test_agent_skills.py -q
```

Result on the pre-implementation test commit: collection failed twice because
`RETIRED_LEGACY_SKILL_REPLACEMENTS` did not exist. This is the intended RED
contract.

Independent adversarial review later found that bootstrap cleanup also matched
every unregistered `spec-kitty-*` directory. Commit `3d0d4bcbf` added a
behavioral regression test with a user-authored
`spec-kitty-user-authored/SKILL.md`; before the fix it failed with
`FileNotFoundError` (`1 failed in 2.51s`).

## GREEN

- Focused registry/bootstrap run: `19 passed in 75.92s`.
- Focused registry/bootstrap/verifier/doctrine/migration run:
  `37 passed in 82.37s`.
- Final delivery-gate rerun on commit `e28399063`: `58 passed in 5.04s`.
- Post-review custom-prefix regression: `1 passed in 47.81s`.
- Post-review registry/bootstrap run on commit `30e790867`: `19 passed in
  2.81s`.
- Ruff: `All checks passed!`.

The obsolete `f238b0882` run remained queued even after an exact cancellation
request, so the new aggregate run could not leave its inherited concurrency
group. The non-destructive fix preserves upstream's group value and gives forks
a stable `fork-<github.ref>` namespace:

- Concurrency behavioral RED: `1 failed in 43.76s`.
- Runner and concurrency contract: `3 passed in 2.04s`.
- Ruff: `All checks passed!`.

The first complete aggregate run then failed its own topology oracle because
the new architectural test file lacked the module-level `architectural` marker:
all three tests had a deterministic `arch_shard_2` assignment but the job's
combined marker expression selected none of them. This is a mission-owned CI
failure, not a baseline exception.

- Cloud RED: `arch-adversarial (arch_shard_2)` reported `1 failed, 683 passed`
  and named all three orphan nodes in `test_fork_runner_portability.py`.
- Local selector RED: `no tests collected (3 deselected)` for
  `architectural and arch_shard_2`.
- After adding `pytestmark = pytest.mark.architectural`, the same selector is
  green: `3 passed in 50.52s`.
- Ruff: `All checks passed!`.
- Mypy: `Success: no issues found in 3 source files`.

All pytest processes used a temporary `USERPROFILE` and
`SPEC_KITTY_HOME`; no real global skill root was a fixture.

## Candidate

- Wheel: `spec_kitty_cli-3.2.6rc4-py3-none-any.whl`
- Size: `8,295,473` bytes
- SHA-256: `F62511C1C46647B652AD67B79FCF623BDA88CBA3C2D643D5955FC066E7D10918`
- Location:
  `C:/Users/Ruslan/AppData/Local/Temp/codex-spec-kitty-retire-legacy-skills-candidates/30e790867/`
- Installed-wheel registry: `DISCOVERED=41 ALIASES=0 REPLACEMENTS=14`.
- Startup bootstrap in both isolated installable roots:
  `ALIASES=0 MISSING=0 CUSTOM_PRESERVED=True`.

This wheel supersedes the earlier `99E68A...D00CE` candidate after the
adversarial-review safety fix.

The initial `--version` smoke was invalid because Typer handles that eager
option before the startup callback. The valid smoke used
`upgrade --agent-check --json` and then inspected only skill directories.

## Local Installation

Installed the superseding verified wheel side-by-side at:

```text
C:/Users/Ruslan/.local/share/spec-kitty-retire-legacy-skills-30e790867/
```

The user launcher `C:/Users/Ruslan/spec-kitty.cmd` now selects that runtime
first while retaining the earlier retirement candidate plus the recovery,
patched, layerfix, and official installations as fallbacks. Its pre-change
copy for this safety update is preserved as:

```text
C:/Users/Ruslan/spec-kitty.cmd.pre-retired-skill-safety-30e790867.bak
```

Real-profile startup verification via `upgrade --agent-check --json`:

- Exit code: `0`.
- Before and after startup: `0` legacy aliases and all `14` canonical
  replacements in `.agents/skills`.
- `.codex/skills/best-step/SKILL.md` SHA-256 was unchanged.
- Launcher version: `spec-kitty-cli version 3.2.6rc4`.
- Runtime import resolved from `spec-kitty-retire-legacy-skills-30e790867`.

The `.codex/skills` root contains neither the package-managed aliases nor their
canonical replacements; the package-managed global surface is `.agents/skills`.

## Fork Delivery

- Remote: `https://github.com/rusliksu/spec-kitty.git`
- Branch: `codex/spec-kitty-retire-legacy-skills`
- Draft PR: `https://github.com/rusliksu/spec-kitty/pull/5`
- Initial published head: `f238b0882b36801bc05667ac27edc7fe07e56f53`
- Base: fork `main`

The PR remains draft. Merge, release, and direct push to `main` were not
performed.

## Independent Review

Three bounded, read-only reviewers (reviewer, architect, and debugger profiles)
independently returned `BLOCK` on the same issue: the prefix-wide cleanup could
delete an unregistered user-authored skill. The fix at `30e790867` limits
cleanup to `RETIRED_CANONICAL_SKILL_NAMES`; tests now preserve an unknown
prefixed skill and exercise current-version-lock cleanup in both `.claude` and
`.agents` roots.

## Fork CI Runner Portability

The fork CI gate was blocked because nine jobs requested
`blacksmith-4vcpu-ubuntu-2404` with an empty `runner_name`. The approved WP03
keeps Blacksmith labels for `Priivacy-ai/spec-kitty` and selects
`ubuntu-latest` or `windows-latest` in forks for the seven PR-triggered
workflow files initially visible as PR checks.

- Behavioral RED: `1 failed in 50.51s` on the first hard-coded runner.
- Focused workflow-policy gate: `50 passed in 6.90s`.
- Ruff on the new architectural test: `All checks passed!`.
- YAML parsing and exact job-to-expression assertions pass for all ten changed
  job definitions.

An exploratory gate-coverage run produced `92 passed, 8 errors`. All eight
errors came from the pre-existing full-suite collection oracle on Windows,
which collected 39,266 tests and then rejected 87 POSIX-only collection errors
including missing `fcntl`; the focused workflow-policy gate is green. The
repository has no pinned `actionlint`, so GitHub's workflow parser and actual
runner assignment remain the external syntax evidence after push.

The first push proved all ten directly changed jobs executed on GitHub-hosted
runners and all eleven reported PR checks passed. It also exposed a previously
hidden workflow-level `CI Quality` run waiting behind an obsolete concurrency
entry. The aggregate workflow and its four reusable module workflows therefore
joined the same approved portability contract:

- Aggregate behavioral RED: `1 failed in 47.22s` on
  `ci-quality.yml:changes`.
- Exact aggregate runner regression: `3 passed in 47.50s`.
- CI-topology and workflow-policy gate: `78 passed, 1 deselected in 21.04s`;
  the deselected node is the same Windows-incompatible full-suite collector
  documented above.
- Ruff: `All checks passed!`.

## Baseline Reporting

An exploratory broad skills-suite run produced `285 passed, 10 failed`. One
failure was attributable to this mission and was fixed by moving its verifier
fixture from retired `spec-kitty` to canonical `spk-start-here`. The remaining
nine failures are in unchanged Windows path/read-only and command-renderer
surfaces.

All nine were independently reproduced from a clean detached worktree at
`origin/main` commit `87d851382fc50cd789ba542b28dbc4bc0fb37618`:

```text
9 failed in 182.99s (0:03:02)
```

The baseline import resolved to that detached worktree, `git status --porcelain`
was empty after the run, and the temporary worktree/profile were removed. See
`traces/pre-existing-skills-suite-failures.md` for the exact node IDs and an
issue-ready report.

The pre-existing-failure reporting gate was satisfied on 2026-09-03:

- `#3771` tracks the read-only `SKILL.md` defect class; the clean-baseline
  reproduction was added as an evidence comment.
- `#3852` tracks the six portable-path failures.
- `#3853` tracks the renderer-frontmatter failure.

These tracker records include the reproduction commands, failure summaries,
and clean-`origin/main` attribution required by repository policy.
