"""Connection-free coalescing over the project-owned journal repository."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from kernel.clock import now_utc_iso

from .journal import CoalesceDecision, EventJournal, register_coalesce_strategy
from .models import Event


class DeliveredAnywhereQuery(Protocol):
    def delivered_anywhere(self, event_id: str) -> bool: ...


# The seam is process-global while a project unit of work is not: both the
# strategy and `install` therefore take a RESOLVER (journal -> query) so the
# answer always comes from the caller's live transaction, never from a ledger
# instance pinned when the seam was installed and closed since.


@dataclass(frozen=True, slots=True)
class SupersedeMarker:
    superseded_event_id: str
    superseded_by_event_id: str
    coalesce_key: str | None
    at: str


def read_supersede_markers(journal: EventJournal) -> list[SupersedeMarker]:
    return [SupersedeMarker(*row) for row in journal.supersede_rows()]


class CoalescingStrategy:
    """Latest-wins coalescing that never mutates a delivered payload."""

    def __init__(self, query_for: Callable[[EventJournal], DeliveredAnywhereQuery]) -> None:
        self._query_for = query_for

    def __call__(self, journal: EventJournal, event: Event) -> CoalesceDecision:
        key = event.coalesce_key
        if key is None:
            return CoalesceDecision()
        candidates = [row for row in journal.read_all() if row.coalesce_key == key]
        if not candidates:
            return CoalesceDecision()
        query = self._query_for(journal)
        undelivered = [candidate for candidate in candidates if not query.delivered_anywhere(candidate.event_id)]
        if undelivered:
            journal.replace_undelivered_payload(undelivered[-1].event_id, event.payload)
            return CoalesceDecision(store_as_new=False)
        journal.record_supersede(
            candidates[-1].event_id,
            event.event_id,
            key,
            now_utc_iso(),
        )
        return CoalesceDecision()


def install(query_for: Callable[[EventJournal], DeliveredAnywhereQuery]) -> CoalescingStrategy:
    strategy = CoalescingStrategy(query_for)
    register_coalesce_strategy(strategy)
    return strategy


__all__ = [
    "DeliveredAnywhereQuery",
    "SupersedeMarker",
    "install",
]
