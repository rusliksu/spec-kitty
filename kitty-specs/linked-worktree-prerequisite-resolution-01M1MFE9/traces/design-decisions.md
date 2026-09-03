# Design Decision Trace

## DD-001 — Shared operation context

Use `resolve_mission_operation_context()` as the single authority for choosing repository and Mission roots.

## DD-002 — Preserve split authorities

Git topology/protection remains anchored to `repository_root`; Mission artifacts use `mission_anchor_root`.

## DD-003 — Consumer migration before resolver rewrite

Move the four reproduced command families onto the existing seam. Change the seam itself only if RED tests reveal a missing invariant.

## DD-004 — Fail closed

Preserve typed ambiguity, missing-selector, unsafe-token, and conflicting-identity failures. Never fall back to a global Mission census after an exact caller-owned hit.

## DD-005 — Sequential lane

The affected consumers share identity fixtures and authority rules, so work remains sequential rather than split into parallel writers.
