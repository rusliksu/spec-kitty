# Mission Specification: Retire Legacy Spec Kitty Skills

**Mission ID**: `01M1KADPHZXDRJA7VMFVYJTEY0`
**Mission Type**: `software-dev`
**Target Branch**: `main`
**Bead**: `spk-8zh`
**Status**: Approved (delivery extension approved 2026-09-03)

## Overview

The Spec Kitty startup bootstrap currently republishes fourteen superseded
`spec-kitty*` skill packages into every user-global agent skill root. The
canonical `spk-*` hierarchy already replaces them. This mission makes those
fourteen names explicitly retired so a fresh startup installs only the
canonical replacements and a migration startup removes stale managed copies.

The original package was source policy, focused migration coverage, and an
isolated built-runtime smoke. On 2026-09-03 Ruslan explicitly extended the
approved scope to install the verified candidate locally, repair his real
global skill root, update the current Bead, and publish the task branch to the
Spec Kitty fork through a draft PR. Merge and release remain separate gates.

## User Scenarios & Testing

### Primary scenario

**Given** a user upgrades to a build containing this policy and runs any
Spec Kitty command, **when** startup synchronizes global agent skills, **then**
none of the fourteen retired aliases is installed and each canonical `spk-*`
replacement remains available.

### Migration scenario

**Given** a global skill root containing stale copies of all fourteen retired
aliases and a current version lock, **when** startup runs, **then** the known
retired paths are removed, canonical skills are synchronized, and unrelated
user skill directories remain byte-identical.

### Exception scenario

Unknown or third-party skill names are outside the retirement contract and
must not be removed. Tests and candidate smoke runs use isolated temporary
homes. The separately approved local-install step may run the verified startup
once against Ruslan's real profile, with a preserved launcher fallback and
before/after evidence.

## Domain Language

- **Retired alias**: one of the exact fourteen package-managed legacy skill
  names listed in the retirement authority.
- **Canonical replacement**: the corresponding public `spk-*` skill.
- **Global bootstrap**: the startup synchronization that populates supported
  user-global agent skill roots.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Canonical skill discovery MUST exclude exactly the fourteen approved retired aliases. | Accepted |
| FR-002 | Startup bootstrap MUST remove stale directories for those aliases even when the agent-skill version lock already matches the running build. | Accepted |
| FR-003 | Startup bootstrap MUST continue to install the corresponding canonical `spk-*` skills. | Accepted |
| FR-004 | Startup bootstrap MUST preserve unrelated skill directories and their contents. | Accepted |
| FR-005 | The retirement authority MUST expose an explicit legacy-to-canonical mapping so tests and future migrations cannot drift into two lists. | Accepted |
| FR-006 | The verified wheel MUST be installed side-by-side and selected by the user launcher while prior runtimes remain available as fallbacks. | Accepted |
| FR-007 | The task branch MUST be published through a draft PR to the fork after targeted gates pass. | Accepted |
| FR-008 | PR-triggered workflows blocking the fork PR MUST retain Blacksmith on `Priivacy-ai/spec-kitty` and select GitHub-hosted runners on forks. | Accepted |

### Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Focused unit and migration tests MUST pass on Windows and remain platform-neutral. | Accepted |
| NFR-002 | The isolated built-wheel bootstrap smoke MUST complete without writing to Ruslan's real global agent roots. | Accepted |
| NFR-003 | The startup fast path MUST remain unchanged when no retired path needs cleanup. | Accepted |
| NFR-004 | The real-profile installation MUST prove zero retired aliases, all canonical replacements, and byte preservation of an unrelated user skill. | Accepted |
| NFR-005 | Fork-runner selection MUST be explicit, repository-scoped, and valid GitHub Actions syntax without weakening upstream runner selection. | Accepted |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Scope is limited to the fourteen aliases approved in this mission. | Accepted |
| C-002 | Local installation and task-branch publication are authorized only for this verified candidate; merge, release, and direct push to `main` remain prohibited. | Accepted |
| C-003 | User-created skills outside the explicit retired-name contract are preserved. | Accepted |
| C-004 | The mission is not a bulk edit: it changes one discovery/retirement policy rather than replacing one token across files. | Accepted |
| C-005 | CI portability is limited to workflows that block draft PR `rusliksu/spec-kitty#5`; unrelated release and scheduled workflows remain unchanged. | Accepted |

## Success Criteria

- **SC-001**: all 14 retired aliases are absent from default registry discovery.
- **SC-002**: all 14 stale alias directories are removed in an isolated
  current-lock migration test.
- **SC-003**: all 14 mapped canonical replacements remain discoverable and at
  least one replacement is proven installed by the bootstrap test.
- **SC-004**: unrelated fixture skills remain byte-identical.
- **SC-005**: targeted pytest, ruff, mypy, wheel inspection, and isolated
  wheel-runtime smoke are green.
- **SC-006**: the local launcher resolves the side-by-side candidate; real
  `.agents/skills` has zero aliases and all 14 canonical replacements while an
  unrelated skill remains byte-identical.
- **SC-007**: a draft PR exposes the exact task-owned branch for fork review.
- **SC-008**: every check triggered by the draft PR either completes on a
  GitHub-hosted fork runner or is skipped by its documented path predicate;
  upstream jobs still resolve to their existing Blacksmith labels.

## Assumptions

- The fourteen legacy names are package-reserved, package-managed aliases; the
  explicit finite retirement set is their managed-path contract.
- Bundled legacy source text may remain in the wheel as migration/reference
  material provided default registry discovery cannot install it.
- A later release process owns versioning and public release. The approved
  local installation is a recoverable side-by-side candidate, not a release.
