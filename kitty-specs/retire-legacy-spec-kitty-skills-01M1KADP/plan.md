# Implementation Plan: Retire Legacy Spec Kitty Skills

## Branch Contract

- Current branch: `codex/spec-kitty-retire-legacy-skills`
- Planning/base branch: `main`
- Final merge target: `main`
- Branch matches target: no, by design; work is isolated in a task branch.

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary surfaces**: canonical skill registry, retirement authority, global
  agent-skill bootstrap tests
- **Test framework**: pytest
- **Quality gates**: targeted pytest, ruff, mypy, wheel build/inspection,
  isolated runtime smoke
- **Packaging**: Hatchling wheel for `spec-kitty-cli`

## Design

1. Add a single explicit mapping from each legacy alias to its canonical
   `spk-*` replacement in `skills/retired.py`; derive the retired-name set from
   that authority.
2. Make `SkillRegistry.discover_skills()` omit retired canonical names by
   default. Keep the bundled source directories available as historical or
   migration material, avoiding a large destructive content deletion.
3. Let the existing bootstrap cleanup seam remove only names in the explicit
   retired set and copy the remaining canonical registry. Its current version-
   lock bypass already guarantees same-version cleanup.
4. Drive the change ATDD-first: commit failing behavioral coverage before any
   production edit, then make the smallest implementation change.
5. Build a wheel and execute bootstrap with an isolated `USERPROFILE` and
   `SPEC_KITTY_HOME`; inspect that aliases are absent and replacements present.
6. After explicit operator approval, publish pre-existing failures to the
   tracker, install the exact verified wheel side-by-side, preserve the prior
   launcher as a fallback, and run one real-profile startup reconciliation.
7. Re-run targeted quality gates and publish the task-owned branch as a draft
   PR to the fork. Do not merge or release.
8. For only the workflows triggered by or reused from the fork PR, select the
   existing Blacksmith label when
   `github.repository == 'Priivacy-ai/spec-kitty'` and the matching
   GitHub-hosted Linux/Windows label otherwise. Validate workflow syntax and
   policy tests, then push to obtain real fork-CI evidence.

## Ownership and Safety

The explicit finite retired-name mapping is the package-managed path contract;
no wildcard is added. Unknown skills remain untouched. Test/runtime smoke work
uses a temporary profile. The approved local installation is side-by-side,
keeps previous runtimes as fallbacks, and preserves a pre-change launcher copy.

## Verification

```text
pytest tests/specify_cli/skills/test_registry.py tests/runtime/test_agent_skills.py
ruff check src/specify_cli/skills/retired.py src/specify_cli/skills/registry.py tests/specify_cli/skills/test_registry.py tests/runtime/test_agent_skills.py
mypy src/specify_cli/skills/retired.py src/specify_cli/skills/registry.py src/specify_cli/runtime/agent_skills.py
python -m build --wheel
pytest tests/architectural/test_fork_runner_portability.py tests/architectural/test_workflow_coherence.py tests/architectural/test_ci_fast_jobs_have_timeout.py tests/architectural/test_suite_jobs_gate_blocking.py tests/docs/test_docs_freshness_invariant.py tests/release/test_release_ci_ownership.py
```

The repository does not pin or install `actionlint`, so GitHub's workflow
parser and actual runner assignment are the external syntax gate after push.

The wheel smoke first runs the built candidate in a temporary virtual
environment and profile. The later approved installation gate additionally
checks the real global root before and after one startup reconciliation.

## Gates

- No implementation before a failing test commit.
- Baseline-red failures must be reported before fork publication.
- Task-branch push, draft PR creation, side-by-side installation, launcher
  selection, and real-profile reconciliation were explicitly approved on
  2026-09-03.
- No direct push to `main`, PR merge, release, destructive fallback cleanup, or
  unrelated global mutation.
- Any need to widen beyond the fourteen names requires a new approval delta.
- The fork-runner portability delta for the blocking PR workflow graph was
  approved by Ruslan on 2026-09-03; ready/merge still require green CI.
