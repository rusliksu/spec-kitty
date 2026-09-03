"""Retired Spec Kitty skill package names."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final


RETIRED_LEGACY_SKILL_REPLACEMENTS: Final = MappingProxyType({
    "spec-kitty": "spk-start-here",
    "spec-kitty-bulk-edit-classification": "spk-doctrine-bulk-edit",
    "spec-kitty-charter-doctrine": "spk-doctrine-charter",
    "spec-kitty-git-workflow": "spk-admin-git-workflow",
    "spec-kitty-glossary-context": "spk-doctrine-glossary",
    "spec-kitty-implement-review": "spk-run-implement-review",
    "spec-kitty-mission-review": "spk-gate-mission-review",
    "spec-kitty-mission-system": "spk-mission-types",
    "spec-kitty-orchestrator-api-operator": "spk-integrate-orchestrator-api",
    "spec-kitty-program-orchestrate": "spk-run-program-orchestrate",
    "spec-kitty-runtime-next": "spk-run-next",
    "spec-kitty-runtime-review": "spk-run-review-wp",
    "spec-kitty-setup-doctor": "spk-admin-setup-doctor",
    "spec-kitty-spdd-reasons": "spk-doctrine-spdd-reasons",
})

RETIRED_STANDALONE_SKILL_NAMES = frozenset({
    "spec-kitty.advise",
})

RETIRED_CANONICAL_SKILL_NAMES = frozenset({
    "debugger-debbie",
    "paula-patterns",
    # Removed by PR #2312 — internal kittyfooding, relocated to spec-kitty-saas#370.
    "spk-team-upsun-cli-sync",
}) | RETIRED_STANDALONE_SKILL_NAMES | frozenset(RETIRED_LEGACY_SKILL_REPLACEMENTS)
