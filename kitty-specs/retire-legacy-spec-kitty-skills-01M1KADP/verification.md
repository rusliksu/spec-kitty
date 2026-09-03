# Verification Evidence

## RED

Command:

```text
python -m pytest tests/specify_cli/skills/test_registry.py tests/runtime/test_agent_skills.py -q
```

Result on the pre-implementation test commit: collection failed twice because
`RETIRED_LEGACY_SKILL_REPLACEMENTS` did not exist. This is the intended RED
contract.

## GREEN

- Focused registry/bootstrap run: `19 passed in 75.92s`.
- Focused registry/bootstrap/verifier/doctrine/migration run:
  `37 passed in 82.37s`.
- Final delivery-gate rerun on commit `e28399063`: `58 passed in 5.04s`.
- Ruff: `All checks passed!`.
- Mypy: `Success: no issues found in 3 source files`.

All pytest processes used a temporary `USERPROFILE` and
`SPEC_KITTY_HOME`; no real global skill root was a fixture.

## Candidate

- Wheel: `spec_kitty_cli-3.2.6rc4-py3-none-any.whl`
- Size: `8,295,502` bytes
- SHA-256: `99E68A2DC683F0F2A026CB20BEBE825C27D1BFBE24E0C09F3C8608B08A2D00CE`
- Location:
  `C:/Users/Ruslan/AppData/Local/Temp/codex-spec-kitty-retire-legacy-skills-candidates/ce9518f47182420197ace8a8f68e8ca5/`
- Installed-wheel registry: `DISCOVERED=41 ALIASES=0 REPLACEMENTS=14`.
- Startup bootstrap in isolated profile:
  `ALIASES_REMAINING=0 CANONICAL_MISSING=0 CUSTOM_PRESERVED=True`.

The initial `--version` smoke was invalid because Typer handles that eager
option before the startup callback. The valid smoke used
`upgrade --agent-check --json` and then inspected only skill directories.

## Local Installation

Installed the verified wheel side-by-side at:

```text
C:/Users/Ruslan/.local/share/spec-kitty-retire-legacy-skills-e3f0846fa/
```

The user launcher `C:/Users/Ruslan/spec-kitty.cmd` now selects that runtime
first while retaining the prior recovery, patched, layerfix, and official
installations as fallbacks. Its pre-change copy is preserved as:

```text
C:/Users/Ruslan/spec-kitty.cmd.pre-retire-legacy-e3f0846fa.bak
```

Real-profile startup verification via `upgrade --agent-check --json`:

- Exit code: `0`.
- Before startup: `14` legacy aliases in `.agents/skills`.
- After startup: `0` legacy aliases and all `14` canonical replacements in
  `.agents/skills`.
- `.codex/skills/best-step/SKILL.md` SHA-256 was unchanged.
- Launcher version: `spec-kitty-cli version 3.2.6rc4`.
- Runtime import resolved from the new side-by-side installation.

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
