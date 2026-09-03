# Mission Specification: Retire Legacy Spec Kitty Skills

**Mission ID**: `01M1KADPHZXDRJA7VMFVYJTEY0`
**Mission Type**: `software-dev`
**Target Branch**: `main`
**Bead**: `spk-8zh`
**Status**: Approved

## Overview

The Spec Kitty startup bootstrap currently republishes fourteen superseded
`spec-kitty*` skill packages into every user-global agent skill root. The
canonical `spk-*` hierarchy already replaces them. This mission makes those
fourteen names explicitly retired so a fresh startup installs only the
canonical replacements and a migration startup removes stale managed copies.

The approved package is source policy, focused migration coverage, and an
isolated built-runtime smoke. It does not install the candidate, change the
launcher, repair Ruslan's real global skill roots, push, or merge.

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
homes; the real user-global roots are not test fixtures.

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

### Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Focused unit and migration tests MUST pass on Windows and remain platform-neutral. | Accepted |
| NFR-002 | The isolated built-wheel bootstrap smoke MUST complete without writing to Ruslan's real global agent roots. | Accepted |
| NFR-003 | The startup fast path MUST remain unchanged when no retired path needs cleanup. | Accepted |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Scope is limited to the fourteen aliases approved in this mission. | Accepted |
| C-002 | No installed runtime, launcher, real global skill root, live service, or remote branch may be mutated. | Accepted |
| C-003 | User-created skills outside the explicit retired-name contract are preserved. | Accepted |
| C-004 | The mission is not a bulk edit: it changes one discovery/retirement policy rather than replacing one token across files. | Accepted |

## Success Criteria

- **SC-001**: all 14 retired aliases are absent from default registry discovery.
- **SC-002**: all 14 stale alias directories are removed in an isolated
  current-lock migration test.
- **SC-003**: all 14 mapped canonical replacements remain discoverable and at
  least one replacement is proven installed by the bootstrap test.
- **SC-004**: unrelated fixture skills remain byte-identical.
- **SC-005**: targeted pytest, ruff, mypy, wheel inspection, and isolated
  wheel-runtime smoke are green.

## Assumptions

- The fourteen legacy names are package-reserved, package-managed aliases; the
  explicit finite retirement set is their managed-path contract.
- Bundled legacy source text may remain in the wheel as migration/reference
  material provided default registry discovery cannot install it.
- A later release process owns versioning and installation. This task produces
  a local candidate only.
