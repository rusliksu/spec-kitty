"""Per-channel reachability properties (WP08, contract §3 R-1..R-6).

The two channels are measured by two different traversals, both **called** from
:mod:`doctrine.drg.reachability` (no walk is reimplemented here):

* **action channel** — :func:`action_channel_reachable`, which calls
  :func:`doctrine.drg.query.resolve_context` at ``d=1`` and ``d=2``.
* **profile channel** — :func:`profile_channel_reachable`, a distinct
  ``walk_edges`` over ``{requires, specializes_from}``. Seeding profiles into
  ``resolve_context`` instead would measure zero (R-3), a fact this module pins
  directly.

The retained assertions encode traversal semantics and named, current wiring
contracts. Historical ever-growing membership snapshots and normalization
counts are intentionally not executable contracts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import load_built_in_graph
from doctrine.drg.models import DRGGraph, Relation
from doctrine.drg.query import resolve_context
from doctrine.drg.reachability import (
    PROFILE_CHANNEL_RELATIONS,
    action_channel_reachable,
    action_seed_urns,
    agent_profile_seed_urns,
    profile_channel_reachable,
)
from reachability_fixtures.nominal_wiring import (
    ACTION_URN,
    IN_SCOPE_DIRECTIVE,
    NOMINALLY_WIRED,
    PROPERLY_WIRED,
    UNREACHABLE_SOURCE,
    incident_urns,
    nominal_wiring_graph,
)

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

#: Repo root — tests/doctrine/drg/ is three levels down.
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: ``resolve_context`` depths: compact (stricter) and bootstrap.
_ACTION_D1_DEPTH = 1
_ACTION_D2_DEPTH = 2

# ---------------------------------------------------------------------------
# WP03 SUPERSEDING NOTE (mission ``doctrine-delivery-activation-01KYQVQK``)
# ---------------------------------------------------------------------------
# The per-family narratives below were authored by the PRIOR mission
# (``doctrine-delivery-reachability-01KYMXD6``) when the profile channel walked
# only {requires, specializes_from}. Their PROFILE-channel asides — "the profile
# channel is unchanged", "_PROFILE_UNREACHABLE unchanged (153)", "measured
# 39->39", "_PROFILE_RESCUES 4 -> 2", and family E's "profile channel walks
# {requires, specializes_from} only" — describe that PRE-WP01 state and are now
# SUPERSEDED. WP01 (FR-001) added ``Relation.SUGGESTS`` to
# ``PROFILE_CHANNEL_RELATIONS``, so the profile channel now follows ``suggests``:
# ``_PROFILE_UNREACHABLE`` is 59 (was 153; 60 until mission
# ``rehome-writing-comms-doctrine-01KZ9V0S`` shipped the DIRECTIVE_050 -> secure-
# design-checklist ``suggests`` edge required by the new ``minutes-maker-mahad``
# profile — see that mission's ledger section in the wiring table) and
# ``_PROFILE_RESCUES`` is 30 (was 2).
# The ACTION-channel claims in these narratives (``_ACTION_UNREACHABLE_D1``/``D2``
# and their family moves) are UNCHANGED and remain accurate — WP02's topology is
# action-inert. See the reconciled ``_PROFILE_UNREACHABLE`` / ``_PROFILE_RESCUES``
# docstrings and the "profile-channel walk-activation" ledger in
# ``docs/plans/doctrine/delivery-reachability-wiring-table.md`` for the live
# profile-channel record. These historical narratives are left in place (not
# edited in situ) to keep the prior mission's action-channel ledger diff legible.

#: The common-docs cluster WP09 wires (mission doctrine-delivery-reachability,
#: T050, FR-015). One authored `scope` edge —
#: ``action:documentation/generate --scope--> directive:DIRECTIVE_042`` — makes
#: DIRECTIVE_042 action-reachable, and 042's pre-existing ``requires``/``suggests``
#: edges then deliver the asset, the styleguide and the four common-docs tactics
#: transitively. These six leave BOTH ``_ACTION_UNREACHABLE_D1`` and
#: ``_ACTION_UNREACHABLE_D2`` (NFR-004 ledger row: the two golden membership sets
#: each shrink by exactly these six; the d1<->d2 spread stays 7 because the same
#: members leave both, and ``_PROFILE_UNREACHABLE`` / ``_PROFILE_RESCUES`` are
#: unaffected — the profile channel is unchanged and all six are profile-
#: unreachable too). The edge's source is an ``action`` node, so it satisfies
#: C-007(b)'s second clause without needing its own reachability measured, and
#: 042's ``scope:`` text ("whenever a documentation file ... is created") attests
#: the relationship to ``documentation/generate``'s ``write_docs`` step (C-007a).
#: ``asset:common-docs-structural-lint`` is delivered but not itself activated, so
#: it is proven reachable directly rather than via the activated-set subtraction.
_COMMON_DOCS_WIRED: frozenset[str] = frozenset(
    {
        "directive:DIRECTIVE_042",
        "styleguide:common-docs",
        "tactic:common-docs-curation",
        "tactic:common-docs-find",
        "tactic:common-docs-scaffold",
        "tactic:common-docs-write",
    }
)

#: The delivery target the wired cluster exists to reach (WP10/WP11 ship assets).
_COMMON_DOCS_ASSET = "asset:common-docs-structural-lint"

#: The DDD family #3063 family-A wires (operator interview outcome, C-007(a)
#: satisfied by operator ruling). One authored ``scope`` edge —
#: ``action:software-dev/specify --scope--> paradigm:domain-driven-design`` —
#: makes the DDD paradigm action-reachable, and the paradigm's ten authored
#: ``requires`` edges (to the strategic-design + tactical DDD members whose own
#: text attests DDD membership) then deliver the family transitively. Every
#: member here becomes action-reachable at BOTH depths after the edge lands;
#: ``tactic:strategic-domain-classification`` was already action-reachable
#: (via ``tactic:paula-patterns-architecture-scout-review``), so it is delivered
#: too but leaves neither ``_ACTION_UNREACHABLE`` set. NOTE the specify edge is
#: ``scope`` NOT ``suggests``: measured with the WP08 helper, a ``suggests`` edge
#: whose SOURCE is an action node is inert — ``resolve_context`` walks ``suggests``
#: only FROM scope-resolved artifacts, never from the action node — so only a
#: ``scope`` edge changes action reachability (the WP09 precedent,
#: ``action:documentation/generate --scope--> directive:DIRECTIVE_042``).
#:
#: NFR-004 ledger for this move: ``_ACTION_UNREACHABLE_D1`` and
#: ``_ACTION_UNREACHABLE_D2`` each lose the SAME twelve members —
#: ``paradigm:domain-driven-design``; its two pre-existing ``directive_refs``
#: ``DIRECTIVE_031``/``DIRECTIVE_032`` (delivered once the paradigm is scoped);
#: and the nine newly-required members that were unreachable
#: (``styleguide:aggregate-design-rules`` + the eight DDD tactics minus
#: ``strategic-domain-classification``, which was already reachable). Because the
#: same twelve leave both, the d1<->d2 spread stays 7. ``_PROFILE_UNREACHABLE`` is
#: unchanged (the profile channel is untouched: the three profile edges are
#: ``suggests``, which that channel does not follow, and the DDD paradigm stays
#: profile-unreachable so its new ``requires`` edges deliver nothing there —
#: measured 39->39). ``_PROFILE_RESCUES`` (defined as
#: ``_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE``) therefore loses the four of
#: its members that just entered the action channel: ``DIRECTIVE_031``,
#: ``DIRECTIVE_032``, ``anti-corruption-layer`` and ``domain-event-capture`` — the
#: action channel now covers them, so they are no longer profile-only rescues.
#: Orphan sets are unaffected (every endpoint was already edge-incident).
_DDD_FAMILY_WIRED: frozenset[str] = frozenset(
    {
        "paradigm:domain-driven-design",
        "tactic:bounded-context-identification",
        "tactic:context-mapping-classification",
        "tactic:context-boundary-inference",
        "tactic:bounded-context-canvas-fill",
        "tactic:aggregate-boundary-design",
        "tactic:entity-value-object-classification",
        "tactic:domain-event-capture",
        "tactic:anti-corruption-layer",
        "tactic:strategic-domain-classification",
        "styleguide:aggregate-design-rules",
    }
)

#: The TESTING / BDD / MUTATION family #3063 family-D delivers (operator interview
#: outcome + ACCEPT-DELIVERY ruling 2026-07-29). Unlike families B/C, family D is
#: reachability-affecting: two hubs are EXISTING action-scoped directives, so their
#: outbound ``suggests`` edges ARE walked and DELIVER at implement/review.
#: ``directive:DIRECTIVE_034`` (test-first) and ``directive:DIRECTIVE_030`` (test-
#: quality gate) are both ``scope``-linked from ``action:software-dev/implement``
#: and ``action:software-dev/review``; ``resolve_context`` step 3 walks ``suggests``
#: from those scope-resolved artifacts.
#:
#: Delivered at BOTH d=1 and d=2 (leave both ``_ACTION_UNREACHABLE`` sets) — five
#: from DIRECTIVE_034 (development-bdd, atdd-adversarial-acceptance,
#: specification-by-example, formalized-constraint-testing, example-mapping-
#: workshop) and two from DIRECTIVE_030 (adversarial-qa-handoff,
#: work-package-completion-validation):
_TESTING_DELIVERED_AT_D1: frozenset[str] = frozenset(
    {
        "tactic:development-bdd",
        "tactic:atdd-adversarial-acceptance",
        "paradigm:specification-by-example",
        "tactic:formalized-constraint-testing",
        "procedure:example-mapping-workshop",
        "tactic:adversarial-qa-handoff",
        "tactic:work-package-completion-validation",
    }
)

#: Delivered at the bootstrap depth d=2 ONLY (leave ``_ACTION_UNREACHABLE_D2`` but
#: NOT ``_ACTION_UNREACHABLE_D1``; they move into the d1<->d2 spread):
#: ``reverse-speccing`` / ``test-to-system-reconstruction`` via the
#: ``paradigm:brownfield-onboarding`` suggests chain, and
#: ``styleguide:mutation-aware-test-design`` via a 2-hop suggests chain out of the
#: action-scoped DIRECTIVE_030.
_TESTING_DELIVERED_AT_D2_ONLY: frozenset[str] = frozenset(
    {
        "tactic:reverse-speccing",
        "tactic:test-to-system-reconstruction",
        "styleguide:mutation-aware-test-design",
    }
)

#: Every artefact family-D makes action-reachable (the union). The BDD + test-
#: quality members action-reachable at implement/review — the acceptance target of
#: the ACCEPT-DELIVERY ruling. The mutation hub (a NEW non-scoped directive) and the
#: DIRECTIVE_041 fan-out stay UNREACHABLE (their members remain in the deferred set);
#: the profile->hub and event-storming edges are ``suggests`` on the profile channel
#: and inert. ``_PROFILE_UNREACHABLE`` is unchanged (153); ``_PROFILE_RESCUES``
#: 4 -> 2 because development-bdd and reverse-speccing entered the action channel.
_TESTING_BDD_MUTATION_WIRED: frozenset[str] = (
    _TESTING_DELIVERED_AT_D1 | _TESTING_DELIVERED_AT_D2_ONLY
)

@pytest.fixture(scope="module")
def graph() -> DRGGraph:
    return load_built_in_graph()


@pytest.mark.doctrine
class TestActionChannelReachability:
    """The action channel is measured by CALLING ``resolve_context`` (R-1)."""

    def test_action_helper_calls_resolve_context_not_a_reimplemented_walk(
        self, graph: DRGGraph
    ) -> None:
        """Union over action seeds equals the per-seed ``resolve_context`` union.

        If the helper reimplemented the walk, this equality against a direct
        ``resolve_context`` union would be the first thing to drift.
        """
        seeds = action_seed_urns(graph)
        assert seeds, "the shipped graph must carry action nodes to seed from"
        direct: set[str] = set()
        for seed in seeds:
            direct |= resolve_context(graph, seed, depth=_ACTION_D1_DEPTH).artifact_urns
        assert action_channel_reachable(graph, seeds, _ACTION_D1_DEPTH) == frozenset(direct)

    def test_common_docs_cluster_and_asset_are_action_reachable(self, graph: DRGGraph) -> None:
        """FR-015 / WP09 acceptance (spec User Story 4, scenario 3): every wired
        artefact is action-reachable AFTER landing, not merely edge-incident.

        The whole common-docs cluster was a strongly-connected island no action
        scoped — measured unreachable at d=1 and d=2 before WP09. The single
        authored ``scope`` edge from ``documentation/generate`` to DIRECTIVE_042
        must make all six activated members AND the delivered asset reachable at
        BOTH depths. Measured by CALLING the WP08 helper (R-1); if any member
        were only edge-incident to an unreachable source (the PR #3007 failure),
        it would be absent from this set and this test would name it.
        """
        for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
            reachable = action_channel_reachable(graph, action_seed_urns(graph), depth)
            missing = sorted((_COMMON_DOCS_WIRED | {_COMMON_DOCS_ASSET}) - reachable)
            assert not missing, (
                f"wired common-docs artefacts still unreachable at d={depth} "
                f"(wired to an unreachable source, or the scope edge is absent): "
                f"{missing}"
            )

    def test_ddd_family_is_action_reachable_at_specify_grain(
        self, graph: DRGGraph
    ) -> None:
        """#3063 family-A acceptance (operator interview outcome): the specify
        grain must reach the DDD paradigm and its strategic-design family.

        The whole DDD family was a set of activated artefacts no action scoped —
        measured unreachable at d=1 and d=2 before this edge. The single authored
        ``scope`` edge from ``software-dev/specify`` to
        ``paradigm:domain-driven-design`` makes the paradigm action-reachable, and
        its authored ``requires`` edges deliver the members transitively. Measured
        by CALLING the WP08 helper (R-1); if any member were only edge-incident to
        an unreachable source (the PR #3007 failure), it would be absent here and
        this test would name it. Red before the edge lands, green after.
        """
        for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
            reachable = action_channel_reachable(graph, action_seed_urns(graph), depth)
            missing = sorted(_DDD_FAMILY_WIRED - reachable)
            assert not missing, (
                f"DDD family still unreachable at d={depth} "
                f"(paradigm not scoped by an action, or a member is wired only to "
                f"an unreachable source): {missing}"
            )

    def test_testing_bdd_family_is_action_reachable_at_implement_review(
        self, graph: DRGGraph
    ) -> None:
        """#3063 family-D acceptance (operator ACCEPT-DELIVERY ruling): the BDD +
        test-quality members must be action-reachable at implement/review.

        Unlike families B/C, family D delivers, because ``directive:DIRECTIVE_034``
        (test-first) and ``directive:DIRECTIVE_030`` (test-quality gate) are already
        ``scope``-linked from ``action:software-dev/implement`` and
        ``action:software-dev/review``. ``resolve_context`` step 3 walks
        ``suggests`` from those scope-resolved artifacts, so the authored
        ``suggests`` edges deliver their targets. Measured by CALLING the WP08
        helper (R-1): the seven core members must be reachable at BOTH the compact
        (d=1) and bootstrap (d=2) depths; the three brownfield/2-hop members are
        reached at the bootstrap depth only. Red before the edges land, green after.
        """
        r_d1 = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D1_DEPTH)
        missing_d1 = sorted(_TESTING_DELIVERED_AT_D1 - r_d1)
        assert not missing_d1, (
            "BDD + test-quality members still unreachable at d=1 "
            f"(a hub is not action-scoped, or an edge is absent): {missing_d1}"
        )

        r_d2 = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D2_DEPTH)
        missing_d2 = sorted(_TESTING_BDD_MUTATION_WIRED - r_d2)
        assert not missing_d2, (
            "family-D delivered members still unreachable at d=2: "
            f"{missing_d2}"
        )
        # The mutation hub (a NEW non-scoped directive) and the DIRECTIVE_041
        # fan-out are INERT by design: their members stay unreachable. Guards
        # against a future edit that accidentally makes the mutation family eager.
        assert "tactic:mutation-testing-workflow" not in r_d2
        assert "styleguide:quadruple-a-test-format" not in r_d2


@pytest.mark.doctrine
class TestProfileChannelReachability:
    """The profile channel is a SEPARATE ``walk_edges`` traversal (R-3)."""

    def test_profile_relations_are_requires_and_specializes_from(self) -> None:
        """The channel follows lineage + hard-dependency + soft-recommendation
        edges — and crucially NOT ``scope``, the relation ``resolve_context``
        seeds on. That absence is why the two channels cannot be folded (R-3).

        ``suggests`` joins the set in mission
        ``doctrine-delivery-activation-01KYQVQK`` (WP01/FR-001): the profile
        channel now delivers the #3063 A–E families that were authored inert.
        """
        assert {r.value for r in PROFILE_CHANNEL_RELATIONS} == {
            "requires",
            "specializes_from",
            "suggests",
        }
        assert Relation.SCOPE not in PROFILE_CHANNEL_RELATIONS

    def test_resolve_context_from_a_profile_reaches_nothing(self, graph: DRGGraph) -> None:
        """The reason the profile channel is not a ``resolve_context`` seed set.

        ``resolve_context`` step 1 walks ``scope`` only, and profiles carry zero
        outbound ``scope``, so seeding a profile into it returns 0 artefacts at
        every depth — folding the channels would silently measure nothing.
        """
        for seed in agent_profile_seed_urns(graph):
            for depth in (_ACTION_D1_DEPTH, _ACTION_D2_DEPTH):
                assert resolve_context(graph, seed, depth=depth).artifact_urns == frozenset()

    def test_profile_channel_is_fail_closed_on_empty_configuration(
        self, graph: DRGGraph
    ) -> None:
        """``profile: str | None`` — an unconfigured caller reaches NOTHING, not
        the whole graph (R-3b: it must not repeat the fail-open shape FR-018
        retires)."""
        assert profile_channel_reachable(graph, frozenset()) == frozenset()


@pytest.mark.doctrine
class TestNominalWiringIsCaughtT047:
    """Wiring an artefact to an unreachable source does not make it reachable.

    This is the WP's reason to exist: an *incidence* check (PR #3007's method)
    reports the nominally-wired artefact fixed; the *reachability* check reports
    it unreachable.
    """

    def test_incidence_calls_the_nominal_wiring_fixed(self) -> None:
        """The wrong method, demonstrated. Both the unreachable source and the
        nominally-wired target are incident to an edge, so incidence de-orphans
        them — the exact false 'fixed' verdict this WP exists to refuse."""
        incident = incident_urns(nominal_wiring_graph())
        assert NOMINALLY_WIRED in incident
        assert UNREACHABLE_SOURCE in incident

    def test_reachability_reports_the_nominal_wiring_unreachable(self) -> None:
        graph = nominal_wiring_graph()
        reachable = action_channel_reachable(graph, [ACTION_URN], _ACTION_D2_DEPTH)
        # The trap: inbound edge from an unreachable source confers no reach.
        assert NOMINALLY_WIRED not in reachable
        assert UNREACHABLE_SOURCE not in reachable

    def test_positive_control_wiring_to_a_reachable_source_does_reach(self) -> None:
        """Guards against a helper that simply refuses every ``requires`` target:
        a directive the action scopes DOES carry reach to what it requires."""
        graph = nominal_wiring_graph()
        reachable = action_channel_reachable(graph, [ACTION_URN], _ACTION_D2_DEPTH)
        assert IN_SCOPE_DIRECTIVE in reachable
        assert PROPERLY_WIRED in reachable
