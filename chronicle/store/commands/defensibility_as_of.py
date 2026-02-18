"""As-of defensibility: GetDefensibilityAsOf(investigation_uid, as_of_date | as_of_event_id). Phase 7."""

import sqlite3
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.protocols import EventStore, ReadModel
from chronicle.store.read_model import SqliteReadModel, apply_event
from chronicle.store.schema import run_read_model_ddl_only

# Cap events for replay (as-of builds ephemeral state in memory)
_AS_OF_EVENT_LIMIT = 20_000


def get_defensibility_as_of(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    *,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
) -> dict[str, Any] | None:
    """GetDefensibilityAsOf: defensibility snapshot at a point in time. Phase 7.
    Either as_of_date (ISO8601) or as_of_event_id must be set. Returns None if investigation not found."""
    if read_model.get_investigation(investigation_uid) is None:
        return None
    if (as_of_date is None) == (as_of_event_id is None):
        raise ChronicleUserError("Exactly one of as_of_date or as_of_event_id must be set")

    events = store.read_by_investigation(investigation_uid, limit=_AS_OF_EVENT_LIMIT)
    # Replay in recorded_at order to match main read model (not occurred_at).
    events.sort(key=lambda e: (e.recorded_at, e.event_id))

    if as_of_date is not None:
        filtered = [e for e in events if e.occurred_at <= as_of_date]
        as_of_label = as_of_date
    else:
        assert as_of_event_id is not None  # validated above: exactly one of date/event_id
        seen = []
        found = False
        for e in events:
            seen.append(e)
            if e.event_id == as_of_event_id:
                found = True
                break
        if not found:
            raise ChronicleUserError(f"as_of_event_id {as_of_event_id!r} not found in investigation stream")
        filtered = seen
        as_of_label = as_of_event_id

    conn = sqlite3.connect(":memory:")
    try:
        run_read_model_ddl_only(conn)
        for event in filtered:
            apply_event(conn, event)
        conn.commit()
        ephemeral_rm = SqliteReadModel(conn)
        claims = ephemeral_rm.list_claims_by_type(
            investigation_uid=investigation_uid, include_withdrawn=False
        )
        result_claims: list[dict[str, Any]] = []
        for claim in claims:
            scorecard = get_defensibility_score(ephemeral_rm, claim.claim_uid)
            if scorecard is not None:
                result_claims.append(
                    {
                        "claim_uid": claim.claim_uid,
                        "defensibility": {
                            "claim_uid": scorecard.claim_uid,
                            "provenance_quality": scorecard.provenance_quality,
                            "corroboration": scorecard.corroboration,
                            "contradiction_status": scorecard.contradiction_status,
                            "temporal_validity": scorecard.temporal_validity,
                            "attribution_posture": scorecard.attribution_posture,
                            "decomposition_precision": scorecard.decomposition_precision,
                            "contradiction_handling": scorecard.contradiction_handling,
                            "knowability": scorecard.knowability,
                        },
                    }
                )
        return {
            "as_of": as_of_label,
            "investigation_uid": investigation_uid,
            "claims": result_claims,
        }
    finally:
        conn.close()
