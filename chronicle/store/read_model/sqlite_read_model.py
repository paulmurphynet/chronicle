"""SqliteReadModel: query API over the read-model tables. Spec 14.4.10."""

import json
import sqlite3

from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.read_model.models import (
    Artifact,
    Checkpoint,
    Claim,
    ClaimAssertion,
    ClaimDecomposition,
    EvidenceItem,
    EvidenceLink,
    EvidenceSourceLink,
    EvidenceSpan,
    EvidenceSupersession,
    EvidenceTrustAssessment,
    Investigation,
    InvestigationGraphLink,
    LinkWithInherited,
    Source,
    Tension,
    TensionSuggestionRow,
    TierHistoryEntry,
)
from chronicle.store.schema import run_read_model_ddl_only


class SqliteReadModel:
    """Read model backed by SQLite (same connection as event store for same-transaction projection)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        run_read_model_ddl_only(conn)

    def upsert_investigation(
        self,
        investigation_uid: str,
        title: str,
        description: str | None,
        created_at: str,
        created_by_actor_id: str,
        tags_json: str | None,
        is_archived: int,
        updated_at: str,
        current_tier: str = "spark",
        tier_changed_at: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO investigation (
                investigation_uid, title, description, created_at, created_by_actor_id,
                tags_json, is_archived, updated_at, current_tier, tier_changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(investigation_uid) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                updated_at = excluded.updated_at,
                tags_json = excluded.tags_json,
                is_archived = excluded.is_archived,
                current_tier = excluded.current_tier,
                tier_changed_at = excluded.tier_changed_at
            """,
            (
                investigation_uid,
                title,
                description,
                created_at,
                created_by_actor_id,
                tags_json,
                is_archived,
                updated_at,
                current_tier,
                tier_changed_at,
            ),
        )

    def get_investigation(self, uid: str) -> Investigation | None:
        row = self._conn.execute(
            """SELECT investigation_uid, title, description, created_at, created_by_actor_id,
               tags_json, is_archived, updated_at, current_tier, tier_changed_at
               FROM investigation WHERE investigation_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return Investigation(
            investigation_uid=row[0],
            title=row[1],
            description=row[2],
            created_at=row[3],
            created_by_actor_id=row[4],
            tags_json=row[5],
            is_archived=row[6],
            updated_at=row[7],
            current_tier=row[8],
            tier_changed_at=row[9],
        )

    def list_investigations(
        self,
        *,
        limit: int | None = None,
        is_archived: bool | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
    ) -> list[Investigation]:
        sql = """SELECT investigation_uid, title, description, created_at, created_by_actor_id,
               tags_json, is_archived, updated_at, current_tier, tier_changed_at
               FROM investigation WHERE 1=1"""
        params: list = []
        if is_archived is not None:
            sql += " AND is_archived = ?"
            params.append(1 if is_archived else 0)
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        sql += " ORDER BY created_at ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(min(limit, MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            Investigation(
                investigation_uid=r[0],
                title=r[1],
                description=r[2],
                created_at=r[3],
                created_by_actor_id=r[4],
                tags_json=r[5],
                is_archived=r[6],
                updated_at=r[7],
                current_tier=r[8],
                tier_changed_at=r[9],
            )
            for r in cur.fetchall()
        ]

    def list_investigations_page(
        self,
        *,
        limit: int,
        after_created_at: str | None = None,
        after_investigation_uid: str | None = None,
        is_archived: bool | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
    ) -> list[Investigation]:
        """Cursor-based investigations page (created_at/investigation_uid ascending)."""
        sql = """SELECT investigation_uid, title, description, created_at, created_by_actor_id,
               tags_json, is_archived, updated_at, current_tier, tier_changed_at
               FROM investigation WHERE 1=1"""
        params: list = []
        if is_archived is not None:
            sql += " AND is_archived = ?"
            params.append(1 if is_archived else 0)
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        if after_created_at is not None:
            cursor_uid = after_investigation_uid or ""
            sql += " AND (created_at > ? OR (created_at = ? AND investigation_uid > ?))"
            params.extend([after_created_at, after_created_at, cursor_uid])
        sql += " ORDER BY created_at ASC, investigation_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            Investigation(
                investigation_uid=r[0],
                title=r[1],
                description=r[2],
                created_at=r[3],
                created_by_actor_id=r[4],
                tags_json=r[5],
                is_archived=r[6],
                updated_at=r[7],
                current_tier=r[8],
                tier_changed_at=r[9],
            )
            for r in cur.fetchall()
        ]

    def list_tier_history(self, investigation_uid: str, limit: int = 100) -> list[TierHistoryEntry]:
        """List tier transitions for an investigation, newest first. Phase 1."""
        cur = self._conn.execute(
            """SELECT investigation_uid, from_tier, to_tier, reason, occurred_at, actor_id, event_id
               FROM tier_history WHERE investigation_uid = ? ORDER BY occurred_at DESC LIMIT ?""",
            (investigation_uid, limit),
        )
        return [
            TierHistoryEntry(
                investigation_uid=row[0],
                from_tier=row[1],
                to_tier=row[2],
                reason=row[3],
                occurred_at=row[4],
                actor_id=row[5],
                event_id=row[6],
            )
            for row in cur.fetchall()
        ]

    def get_evidence_item(self, uid: str) -> EvidenceItem | None:
        row = self._conn.execute(
            """SELECT evidence_uid, investigation_uid, created_at, ingested_by_actor_id,
               content_hash, file_size_bytes, original_filename, uri, media_type,
               extraction_version, file_metadata_json, metadata_json,
               integrity_status, last_verified_at, updated_at,
               redaction_reason, redaction_at, reviewed_at, reviewed_by_actor_id,
               provenance_type
               FROM evidence_item WHERE evidence_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return EvidenceItem(
            evidence_uid=row[0],
            investigation_uid=row[1],
            created_at=row[2],
            ingested_by_actor_id=row[3],
            content_hash=row[4],
            file_size_bytes=row[5],
            original_filename=row[6],
            uri=row[7],
            media_type=row[8],
            extraction_version=row[9],
            file_metadata_json=row[10],
            metadata_json=row[11],
            integrity_status=row[12],
            last_verified_at=row[13],
            updated_at=row[14],
            redaction_reason=row[15] if len(row) > 15 else None,
            redaction_at=row[16] if len(row) > 16 else None,
            reviewed_at=row[17] if len(row) > 17 else None,
            reviewed_by_actor_id=row[18] if len(row) > 18 else None,
            provenance_type=row[19] if len(row) > 19 else None,
        )

    def list_evidence_by_investigation(
        self,
        investigation_uid: str,
        *,
        created_since: str | None = None,
        created_before: str | None = None,
        ingested_by_actor_id: str | None = None,
        limit: int | None = None,
    ) -> list[EvidenceItem]:
        """Return evidence items for an investigation in created_at order. Optional filters: created_since/created_before (ISO8601), ingested_by_actor_id, limit. Phase C.1: redaction. Phase D.2: reviewed. E2.3: provenance_type."""
        sql = """SELECT evidence_uid, investigation_uid, created_at, ingested_by_actor_id,
               content_hash, file_size_bytes, original_filename, uri, media_type,
               extraction_version, file_metadata_json, metadata_json,
               integrity_status, last_verified_at, updated_at,
               redaction_reason, redaction_at, reviewed_at, reviewed_by_actor_id,
               provenance_type
               FROM evidence_item WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        if ingested_by_actor_id is not None:
            sql += " AND ingested_by_actor_id = ?"
            params.append(ingested_by_actor_id)
        sql += " ORDER BY created_at ASC"
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params.append(min(limit, MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            EvidenceItem(
                evidence_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                ingested_by_actor_id=r[3],
                content_hash=r[4],
                file_size_bytes=r[5],
                original_filename=r[6],
                uri=r[7],
                media_type=r[8],
                extraction_version=r[9],
                file_metadata_json=r[10],
                metadata_json=r[11],
                integrity_status=r[12],
                last_verified_at=r[13],
                updated_at=r[14],
                redaction_reason=r[15] if len(r) > 15 else None,
                redaction_at=r[16] if len(r) > 16 else None,
                reviewed_at=r[17] if len(r) > 17 else None,
                reviewed_by_actor_id=r[18] if len(r) > 18 else None,
                provenance_type=r[19] if len(r) > 19 else None,
            )
            for r in cur.fetchall()
        ]

    def list_evidence_by_investigation_page(
        self,
        investigation_uid: str,
        *,
        limit: int,
        after_created_at: str | None = None,
        after_evidence_uid: str | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
        ingested_by_actor_id: str | None = None,
    ) -> list[EvidenceItem]:
        """Cursor-based evidence page (created_at/evidence_uid ascending)."""
        sql = """SELECT evidence_uid, investigation_uid, created_at, ingested_by_actor_id,
               content_hash, file_size_bytes, original_filename, uri, media_type,
               extraction_version, file_metadata_json, metadata_json,
               integrity_status, last_verified_at, updated_at,
               redaction_reason, redaction_at, reviewed_at, reviewed_by_actor_id,
               provenance_type
               FROM evidence_item WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        if ingested_by_actor_id is not None:
            sql += " AND ingested_by_actor_id = ?"
            params.append(ingested_by_actor_id)
        if after_created_at is not None:
            cursor_uid = after_evidence_uid or ""
            sql += " AND (created_at > ? OR (created_at = ? AND evidence_uid > ?))"
            params.extend([after_created_at, after_created_at, cursor_uid])
        sql += " ORDER BY created_at ASC, evidence_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            EvidenceItem(
                evidence_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                ingested_by_actor_id=r[3],
                content_hash=r[4],
                file_size_bytes=r[5],
                original_filename=r[6],
                uri=r[7],
                media_type=r[8],
                extraction_version=r[9],
                file_metadata_json=r[10],
                metadata_json=r[11],
                integrity_status=r[12],
                last_verified_at=r[13],
                updated_at=r[14],
                redaction_reason=r[15] if len(r) > 15 else None,
                redaction_at=r[16] if len(r) > 16 else None,
                reviewed_at=r[17] if len(r) > 17 else None,
                reviewed_by_actor_id=r[18] if len(r) > 18 else None,
                provenance_type=r[19] if len(r) > 19 else None,
            )
            for r in cur.fetchall()
        ]

    def list_claims_by_type(
        self,
        claim_type: str | None = None,
        investigation_uid: str | None = None,
        limit: int | None = None,
        include_withdrawn: bool = True,
        *,
        created_since: str | None = None,
        created_before: str | None = None,
        created_by_actor_id: str | None = None,
    ) -> list[Claim]:
        """List claims optionally filtered by type, investigation, time range, or actor. Spec 1.5.2. When include_withdrawn is False, only ACTIVE claims returned."""
        effective_limit = min(limit, MAX_LIST_LIMIT) if limit is not None else None
        sql = """SELECT claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text,
               claim_type, scope_json, temporal_json, current_status, language, tags_json, notes,
               parent_claim_uid, decomposition_status, epistemic_stance, updated_at FROM claim WHERE 1=1"""
        params: list = []
        if claim_type is not None:
            sql += " AND claim_type = ?"
            params.append(claim_type)
        if investigation_uid is not None:
            sql += " AND investigation_uid = ?"
            params.append(investigation_uid)
        if not include_withdrawn:
            sql += " AND current_status = 'ACTIVE'"
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        if created_by_actor_id is not None:
            sql += " AND created_by_actor_id = ?"
            params.append(created_by_actor_id)
        sql += " ORDER BY updated_at DESC, claim_uid ASC"
        if effective_limit is not None:
            sql += " LIMIT ?"
            params.append(effective_limit)
        cur = self._conn.execute(sql, params)
        return [
            Claim(
                claim_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                created_by_actor_id=r[3],
                claim_text=r[4],
                claim_type=r[5],
                scope_json=r[6],
                temporal_json=r[7],
                current_status=r[8],
                language=r[9],
                tags_json=r[10],
                notes=r[11],
                parent_claim_uid=r[12],
                decomposition_status=r[13],
                epistemic_stance=r[14] if len(r) > 14 else None,
                updated_at=r[15] if len(r) > 15 else r[14],
            )
            for r in cur.fetchall()
        ]

    def list_claims_page(
        self,
        investigation_uid: str,
        *,
        limit: int,
        include_withdrawn: bool = True,
        before_updated_at: str | None = None,
        before_claim_uid: str | None = None,
    ) -> list[Claim]:
        """Cursor-based claims page (updated_at DESC / claim_uid ASC)."""
        sql = """SELECT claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text,
               claim_type, scope_json, temporal_json, current_status, language, tags_json, notes,
               parent_claim_uid, decomposition_status, epistemic_stance, updated_at
               FROM claim WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if not include_withdrawn:
            sql += " AND current_status = 'ACTIVE'"
        if before_updated_at is not None:
            cursor_uid = before_claim_uid or ""
            sql += " AND (updated_at < ? OR (updated_at = ? AND claim_uid > ?))"
            params.extend([before_updated_at, before_updated_at, cursor_uid])
        sql += " ORDER BY updated_at DESC, claim_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            Claim(
                claim_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                created_by_actor_id=r[3],
                claim_text=r[4],
                claim_type=r[5],
                scope_json=r[6],
                temporal_json=r[7],
                current_status=r[8],
                language=r[9],
                tags_json=r[10],
                notes=r[11],
                parent_claim_uid=r[12],
                decomposition_status=r[13],
                epistemic_stance=r[14] if len(r) > 14 else None,
                updated_at=r[15] if len(r) > 15 else r[14],
            )
            for r in cur.fetchall()
        ]

    def search_claims(
        self,
        investigation_uid: str,
        query: str,
        limit: int = 50,
    ) -> list[Claim]:
        """Full-text search claims in an investigation. Phase 8. Uses FTS5; returns claims matching query."""
        query = (query or "").strip()
        if not query:
            return []
        effective_limit = min(limit, MAX_LIST_LIMIT) if limit else 50
        # FTS5 MATCH ?; join claim to filter by investigation and get full row (DISTINCT to dedupe FTS rows)
        try:
            cur = self._conn.execute(
                """
                SELECT c.claim_uid, c.investigation_uid, c.created_at, c.created_by_actor_id, c.claim_text,
                       c.claim_type, c.scope_json, c.temporal_json, c.current_status, c.language, c.tags_json,
                       c.notes, c.parent_claim_uid, c.decomposition_status, c.epistemic_stance, c.updated_at
                FROM claim c
                INNER JOIN (
                    SELECT DISTINCT claim_uid FROM claim_fts WHERE claim_fts MATCH ? LIMIT ?
                ) f ON c.claim_uid = f.claim_uid
                WHERE c.investigation_uid = ?
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (query, effective_limit * 2, investigation_uid, effective_limit),
            )
        except sqlite3.OperationalError:
            # Malformed FTS query or syntax error; return empty rather than leaking error
            return []
        return [
            Claim(
                claim_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                created_by_actor_id=r[3],
                claim_text=r[4],
                claim_type=r[5],
                scope_json=r[6],
                temporal_json=r[7],
                current_status=r[8],
                language=r[9],
                tags_json=r[10],
                notes=r[11],
                parent_claim_uid=r[12],
                decomposition_status=r[13],
                epistemic_stance=r[14] if len(r) > 14 else None,
                updated_at=r[15] if len(r) > 15 else r[14],
            )
            for r in cur.fetchall()
        ]

    def get_claim(self, uid: str) -> Claim | None:
        row = self._conn.execute(
            """SELECT claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text,
               claim_type, scope_json, temporal_json, current_status, language, tags_json, notes,
               parent_claim_uid, decomposition_status, epistemic_stance, updated_at FROM claim WHERE claim_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return Claim(
            claim_uid=row[0],
            investigation_uid=row[1],
            created_at=row[2],
            created_by_actor_id=row[3],
            claim_text=row[4],
            claim_type=row[5],
            scope_json=row[6],
            temporal_json=row[7],
            current_status=row[8],
            language=row[9],
            tags_json=row[10],
            notes=row[11],
            parent_claim_uid=row[12],
            decomposition_status=row[13],
            epistemic_stance=row[14] if len(row) > 14 else None,
            updated_at=row[15] if len(row) > 15 else row[14],
        )

    def get_evidence_span(self, uid: str) -> EvidenceSpan | None:
        row = self._conn.execute(
            "SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, created_by_actor_id, source_event_id FROM evidence_span WHERE span_uid = ?",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return EvidenceSpan(
            span_uid=row[0],
            evidence_uid=row[1],
            anchor_type=row[2],
            anchor_json=row[3],
            created_at=row[4],
            created_by_actor_id=row[5],
            source_event_id=row[6],
        )

    def list_spans_for_evidence(self, evidence_uid: str, limit: int = 500) -> list[EvidenceSpan]:
        """Return spans for an evidence item (for linking in UI)."""
        cur = self._conn.execute(
            """SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, created_by_actor_id, source_event_id
               FROM evidence_span WHERE evidence_uid = ? ORDER BY created_at ASC LIMIT ?""",
            (evidence_uid, min(limit, MAX_LIST_LIMIT)),
        )
        return [
            EvidenceSpan(
                span_uid=r[0],
                evidence_uid=r[1],
                anchor_type=r[2],
                anchor_json=r[3],
                created_at=r[4],
                created_by_actor_id=r[5],
                source_event_id=r[6],
            )
            for r in cur.fetchall()
        ]

    def get_support_for_claim(self, claim_uid: str) -> list[EvidenceLink]:
        return self._get_links_for_claim(claim_uid, "SUPPORTS")

    def get_challenges_for_claim(self, claim_uid: str) -> list[EvidenceLink]:
        return self._get_links_for_claim(claim_uid, "CHALLENGES")

    def get_child_claims(self, claim_uid: str) -> list[Claim]:
        """Return claims that have this claim as parent. Spec 1.5.2."""
        cur = self._conn.execute(
            """SELECT claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text,
               claim_type, scope_json, temporal_json, current_status, language, tags_json, notes,
               parent_claim_uid, decomposition_status, epistemic_stance, updated_at FROM claim WHERE parent_claim_uid = ? ORDER BY created_at ASC""",
            (claim_uid,),
        )
        return [
            Claim(
                claim_uid=r[0],
                investigation_uid=r[1],
                created_at=r[2],
                created_by_actor_id=r[3],
                claim_text=r[4],
                claim_type=r[5],
                scope_json=r[6],
                temporal_json=r[7],
                current_status=r[8],
                language=r[9],
                tags_json=r[10],
                notes=r[11],
                parent_claim_uid=r[12],
                decomposition_status=r[13],
                epistemic_stance=r[14] if len(r) > 14 else None,
                updated_at=r[15] if len(r) > 15 else r[14],
            )
            for r in cur.fetchall()
        ]

    def get_parent_claim(self, claim_uid: str) -> Claim | None:
        """Return the parent claim if this claim is a child. Spec 1.5.2."""
        claim = self.get_claim(claim_uid)
        if claim is None or claim.parent_claim_uid is None:
            return None
        return self.get_claim(claim.parent_claim_uid)

    def get_inherited_links(self, claim_uid: str) -> list[EvidenceLink]:
        """Return evidence links attached to this claim's parent (inherited by this child). Spec 1.5.2, 3.1.4."""
        parent = self.get_parent_claim(claim_uid)
        if parent is None:
            return []
        support = self._get_links_for_claim(parent.claim_uid, "SUPPORTS")
        challenge = self._get_links_for_claim(parent.claim_uid, "CHALLENGES")
        return support + challenge

    def get_support_for_claim_including_inherited(self, claim_uid: str) -> list[LinkWithInherited]:
        """Return support links for claim, with inherited from parent marked. Spec 3.1.4."""
        direct = self.get_support_for_claim(claim_uid)
        parent = self.get_parent_claim(claim_uid)
        inherited = self.get_support_for_claim(parent.claim_uid) if parent else []
        return [(link, False) for link in direct] + [(link, True) for link in inherited]

    def get_challenges_for_claim_including_inherited(
        self, claim_uid: str
    ) -> list[LinkWithInherited]:
        """Return challenge links for claim, with inherited from parent marked. Spec 3.1.4."""
        direct = self.get_challenges_for_claim(claim_uid)
        parent = self.get_parent_claim(claim_uid)
        inherited = self.get_challenges_for_claim(parent.claim_uid) if parent else []
        return [(link, False) for link in direct] + [(link, True) for link in inherited]

    def get_retracted_links_for_claim(self, claim_uid: str) -> list[dict]:
        """Return support/challenge links that have been retracted for this claim (A1: for reasoning brief)."""
        cur = self._conn.execute(
            """SELECT el.link_uid, el.link_type, r.retracted_at, r.rationale,
                      ei.original_filename, ei.uri, ei.evidence_uid
               FROM evidence_link el
               JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
               JOIN evidence_span es ON el.span_uid = es.span_uid
               JOIN evidence_item ei ON es.evidence_uid = ei.evidence_uid
               WHERE el.claim_uid = ?
               ORDER BY r.retracted_at ASC""",
            (claim_uid,),
        )
        return [
            {
                "link_uid": row[0],
                "link_type": row[1],
                "retracted_at": row[2],
                "rationale": row[3],
                "original_filename": row[4],
                "uri": row[5],
                "evidence_uid": row[6],
            }
            for row in cur.fetchall()
        ]

    def get_latest_claim_decomposition(self, claim_uid: str) -> ClaimDecomposition | None:
        """Return latest decomposition analysis for claim by analyzed_at. Spec 14.4.9."""
        row = self._conn.execute(
            """SELECT analysis_uid, claim_uid, is_atomic, overall_confidence, analysis_rationale,
               suggested_splits, analyzed_at, analyzer_module_id, analyzer_version, run_id
               FROM claim_decomposition WHERE claim_uid = ? ORDER BY analyzed_at DESC LIMIT 1""",
            (claim_uid,),
        ).fetchone()
        if not row:
            return None
        return ClaimDecomposition(
            analysis_uid=row[0],
            claim_uid=row[1],
            is_atomic=row[2],
            overall_confidence=row[3],
            analysis_rationale=row[4],
            suggested_splits=row[5],
            analyzed_at=row[6],
            analyzer_module_id=row[7],
            analyzer_version=row[8],
            run_id=row[9],
        )

    def get_claim_decomposition_by_analysis_uid(
        self, analysis_uid: str
    ) -> ClaimDecomposition | None:
        """Return decomposition analysis by analysis_uid (event_id of ClaimDecompositionAnalyzed). Phase 2."""
        row = self._conn.execute(
            """SELECT analysis_uid, claim_uid, is_atomic, overall_confidence, analysis_rationale,
               suggested_splits, analyzed_at, analyzer_module_id, analyzer_version, run_id
               FROM claim_decomposition WHERE analysis_uid = ?""",
            (analysis_uid,),
        ).fetchone()
        if not row:
            return None
        return ClaimDecomposition(
            analysis_uid=row[0],
            claim_uid=row[1],
            is_atomic=row[2],
            overall_confidence=row[3],
            analysis_rationale=row[4],
            suggested_splits=row[5],
            analyzed_at=row[6],
            analyzer_module_id=row[7],
            analyzer_version=row[8],
            run_id=row[9],
        )

    def list_supersessions_for_evidence(self, evidence_uid: str) -> list[EvidenceSupersession]:
        """Return supersessions where evidence is prior or new. Spec 14.4.7."""
        cur = self._conn.execute(
            """SELECT supersession_uid, new_evidence_uid, prior_evidence_uid, supersession_type, reason, created_at, created_by_actor_id, source_event_id
               FROM evidence_supersession WHERE prior_evidence_uid = ? OR new_evidence_uid = ? ORDER BY created_at ASC""",
            (evidence_uid, evidence_uid),
        )
        return [
            EvidenceSupersession(
                supersession_uid=r[0],
                new_evidence_uid=r[1],
                prior_evidence_uid=r[2],
                supersession_type=r[3],
                reason=r[4],
                created_at=r[5],
                created_by_actor_id=r[6],
                source_event_id=r[7],
            )
            for r in cur.fetchall()
        ]

    def get_source(self, uid: str) -> Source | None:
        """Return source by uid or None. Spec 1.5.2."""
        row = self._conn.execute(
            """SELECT source_uid, investigation_uid, display_name, source_type, alias, encrypted_identity, notes, independence_notes, reliability_notes, created_at, created_by_actor_id, updated_at
               FROM source WHERE source_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return Source(
            source_uid=row[0],
            investigation_uid=row[1],
            display_name=row[2],
            source_type=row[3],
            alias=row[4],
            encrypted_identity=row[5],
            notes=row[6],
            independence_notes=row[7] if len(row) > 7 else None,
            created_at=row[9] if len(row) > 9 else row[8],
            created_by_actor_id=row[10] if len(row) > 10 else row[9],
            updated_at=row[11] if len(row) > 11 else row[10],
            reliability_notes=row[8] if len(row) > 8 else None,
        )

    def list_sources_by_investigation(self, investigation_uid: str) -> list[Source]:
        """Return sources for an investigation in created_at order. Spec 1.5.2."""
        cur = self._conn.execute(
            """SELECT source_uid, investigation_uid, display_name, source_type, alias, encrypted_identity, notes, independence_notes, reliability_notes, created_at, created_by_actor_id, updated_at
               FROM source WHERE investigation_uid = ? ORDER BY created_at ASC""",
            (investigation_uid,),
        )
        return [
            Source(
                source_uid=r[0],
                investigation_uid=r[1],
                display_name=r[2],
                source_type=r[3],
                alias=r[4],
                encrypted_identity=r[5],
                notes=r[6],
                independence_notes=r[7] if len(r) > 7 else None,
                created_at=r[9] if len(r) > 9 else r[8],
                created_by_actor_id=r[10] if len(r) > 10 else r[9],
                updated_at=r[11] if len(r) > 11 else r[10],
                reliability_notes=r[8] if len(r) > 8 else None,
            )
            for r in cur.fetchall()
        ]

    def get_claim_uids_linked_to_evidence(self, evidence_uid: str) -> list[str]:
        """Return claim UIDs that have support/challenge links via spans on this evidence."""
        cur = self._conn.execute(
            """SELECT DISTINCT el.claim_uid FROM evidence_link el
               JOIN evidence_span es ON el.span_uid = es.span_uid WHERE es.evidence_uid = ?""",
            (evidence_uid,),
        )
        return [r[0] for r in cur.fetchall()]

    def list_story_package_tags(self, investigation_uid: str) -> list[str]:
        """Return distinct tag values from claims' tags_json (for story-package view). Phase E.1. Tags are from JSON arrays."""
        claims = self.list_claims_by_type(investigation_uid=investigation_uid, limit=MAX_LIST_LIMIT)
        tags: set[str] = set()
        for c in claims:
            if not c.tags_json:
                continue
            try:
                parsed = json.loads(c.tags_json)
                if isinstance(parsed, list):
                    for t in parsed:
                        if isinstance(t, str) and t.strip():
                            tags.add(t.strip())
            except (json.JSONDecodeError, TypeError):
                continue
        return sorted(tags)

    def list_claims_for_story_package(
        self, investigation_uid: str, tag: str, limit: int = 500
    ) -> list[Claim]:
        """Return claims that have the given tag in tags_json. Phase E.1."""
        claims = self.list_claims_by_type(
            investigation_uid=investigation_uid, limit=min(limit, MAX_LIST_LIMIT)
        )
        tag_clean = tag.strip()
        out: list[Claim] = []
        for c in claims:
            if not c.tags_json:
                continue
            try:
                parsed = json.loads(c.tags_json)
                if isinstance(parsed, list) and tag_clean in [
                    str(t).strip() for t in parsed if isinstance(t, str)
                ]:
                    out.append(c)
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    def list_evidence_uids_linked_to_claims(self, claim_uids: list[str]) -> list[str]:
        """Return distinct evidence UIDs linked (support or challenge) to any of the given claims. Phase E.1."""
        if not claim_uids:
            return []
        placeholders = ",".join("?" for _ in claim_uids)
        cur = self._conn.execute(
            f"""SELECT DISTINCT es.evidence_uid FROM evidence_link el
                JOIN evidence_span es ON el.span_uid = es.span_uid
                LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
                WHERE el.claim_uid IN ({placeholders}) AND r.link_uid IS NULL""",
            claim_uids,
        )
        return [r[0] for r in cur.fetchall()]

    def list_claim_uids_with_support_from_evidence_uids(
        self, evidence_uids: list[str]
    ) -> list[str]:
        """Return claim UIDs that have at least one support link from spans on any of these evidence items (Phase 2: source reliability)."""
        if not evidence_uids:
            return []
        placeholders = ",".join("?" for _ in evidence_uids)
        cur = self._conn.execute(
            f"""SELECT DISTINCT el.claim_uid FROM evidence_link el
                JOIN evidence_span es ON el.span_uid = es.span_uid
                LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
                WHERE es.evidence_uid IN ({placeholders}) AND el.link_type = 'SUPPORTS' AND r.link_uid IS NULL""",
            evidence_uids,
        )
        return [r[0] for r in cur.fetchall()]

    def list_evidence_uids_for_source(self, source_uid: str) -> list[str]:
        """Return evidence UIDs linked to this source (Phase 2: source reliability)."""
        cur = self._conn.execute(
            "SELECT evidence_uid FROM evidence_source_link WHERE source_uid = ? ORDER BY evidence_uid",
            (source_uid,),
        )
        return [r[0] for r in cur.fetchall()]

    def list_evidence_source_links(self, evidence_uid: str) -> list[EvidenceSourceLink]:
        """Return evidence-source links for an evidence item (sources linked to this evidence)."""
        cur = self._conn.execute(
            """SELECT evidence_uid, source_uid, relationship, created_at, source_event_id
               FROM evidence_source_link WHERE evidence_uid = ? ORDER BY created_at ASC""",
            (evidence_uid,),
        )
        return [
            EvidenceSourceLink(
                evidence_uid=r[0],
                source_uid=r[1],
                relationship=r[2],
                created_at=r[3],
                source_event_id=r[4],
            )
            for r in cur.fetchall()
        ]

    def list_assessments_for_evidence(self, evidence_uid: str) -> list[EvidenceTrustAssessment]:
        """Return all trust assessments for an evidence item. Spec evidence-trust-assessments.md."""
        cur = self._conn.execute(
            """SELECT evidence_uid, provider_id, assessment_kind, result, assessed_at,
                      result_expires_at, metadata, source_event_id
               FROM evidence_trust_assessment WHERE evidence_uid = ? ORDER BY assessed_at ASC""",
            (evidence_uid,),
        )
        return [
            EvidenceTrustAssessment(
                evidence_uid=r[0],
                provider_id=r[1],
                assessment_kind=r[2],
                result=json.loads(r[3]) if r[3] else {},
                assessed_at=r[4],
                result_expires_at=r[5],
                metadata=json.loads(r[6]) if r[6] else None,
                source_event_id=r[7],
            )
            for r in cur.fetchall()
        ]

    def get_latest_assessments_for_evidence(
        self, evidence_uid: str
    ) -> list[EvidenceTrustAssessment]:
        """Return latest trust assessment per (provider_id, assessment_kind) for this evidence. Table stores latest per key (upsert)."""
        return self.list_assessments_for_evidence(evidence_uid)

    def get_artifact(self, uid: str) -> Artifact | None:
        """Return artifact by uid or None. Spec 1.5.2."""
        row = self._conn.execute(
            """SELECT artifact_uid, investigation_uid, artifact_type, title, created_at, created_by_actor_id, notes, updated_at
               FROM artifact WHERE artifact_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return Artifact(
            artifact_uid=row[0],
            investigation_uid=row[1],
            artifact_type=row[2],
            title=row[3],
            created_at=row[4],
            created_by_actor_id=row[5],
            notes=row[6],
            updated_at=row[7],
        )

    def list_artifacts_by_investigation(self, investigation_uid: str) -> list[Artifact]:
        """Return artifacts for an investigation in created_at order."""
        cur = self._conn.execute(
            """SELECT artifact_uid, investigation_uid, artifact_type, title, created_at, created_by_actor_id, notes, updated_at
               FROM artifact WHERE investigation_uid = ? ORDER BY created_at ASC""",
            (investigation_uid,),
        )
        return [
            Artifact(
                artifact_uid=r[0],
                investigation_uid=r[1],
                artifact_type=r[2],
                title=r[3],
                created_at=r[4],
                created_by_actor_id=r[5],
                notes=r[6],
                updated_at=r[7],
            )
            for r in cur.fetchall()
        ]

    def get_checkpoint(self, uid: str) -> Checkpoint | None:
        """Return checkpoint by uid or None. Spec 1.5.2. Phase A: policy_summary. E5.3: certification."""
        row = self._conn.execute(
            """SELECT checkpoint_uid, investigation_uid, scope_refs_json, artifact_refs_json, reason, created_at, created_by_actor_id, policy_summary, certifying_org_id, certified_at
               FROM checkpoint WHERE checkpoint_uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return Checkpoint(
            checkpoint_uid=row[0],
            investigation_uid=row[1],
            scope_refs_json=row[2],
            artifact_refs_json=row[3],
            reason=row[4],
            created_at=row[5],
            created_by_actor_id=row[6],
            policy_summary=row[7] if len(row) > 7 else None,
            certifying_org_id=row[8] if len(row) > 8 else None,
            certified_at=row[9] if len(row) > 9 else None,
        )

    def list_checkpoints(self, investigation_uid: str, limit: int = 500) -> list[Checkpoint]:
        """Return checkpoints for an investigation in created_at desc order. Phase 5. Phase A: policy_summary. E5.3: certification."""
        cur = self._conn.execute(
            """SELECT checkpoint_uid, investigation_uid, scope_refs_json, artifact_refs_json, reason, created_at, created_by_actor_id, policy_summary, certifying_org_id, certified_at
               FROM checkpoint WHERE investigation_uid = ? ORDER BY created_at DESC LIMIT ?""",
            (investigation_uid, limit),
        )
        return [
            Checkpoint(
                checkpoint_uid=r[0],
                investigation_uid=r[1],
                scope_refs_json=r[2],
                artifact_refs_json=r[3],
                reason=r[4],
                created_at=r[5],
                created_by_actor_id=r[6],
                policy_summary=r[7] if len(r) > 7 else None,
                certifying_org_id=r[8] if len(r) > 8 else None,
                certified_at=r[9] if len(r) > 9 else None,
            )
            for r in cur.fetchall()
        ]

    def is_artifact_frozen_at_checkpoint(self, checkpoint_uid: str, artifact_uid: str) -> bool:
        """Return True if this artifact is already frozen at this checkpoint (for FreezeArtifactVersion validation)."""
        row = self._conn.execute(
            "SELECT 1 FROM checkpoint_artifact_freeze WHERE checkpoint_uid = ? AND artifact_uid = ?",
            (checkpoint_uid, artifact_uid),
        ).fetchone()
        return row is not None

    def get_checkpoint_freeze_snapshot(self, checkpoint_uid: str) -> dict[str, list[str]]:
        """Aggregate claim_refs, evidence_refs, tension_refs from all artifact freezes at this checkpoint. Phase 6."""
        cur = self._conn.execute(
            """SELECT claim_refs_json, evidence_refs_json, tension_refs_json
               FROM checkpoint_artifact_freeze WHERE checkpoint_uid = ?""",
            (checkpoint_uid,),
        )
        claim_refs: list[str] = []
        evidence_refs: list[str] = []
        tension_refs: list[str] = []
        for row in cur.fetchall():
            for refs_json, out_list in [
                (row[0], claim_refs),
                (row[1], evidence_refs),
                (row[2], tension_refs),
            ]:
                if refs_json:
                    try:
                        parsed = json.loads(refs_json)
                        if isinstance(parsed, list):
                            for r in parsed:
                                if r and r not in out_list:
                                    out_list.append(r)
                    except (TypeError, ValueError):
                        pass
        return {
            "claim_refs": claim_refs,
            "evidence_refs": evidence_refs,
            "tension_refs": tension_refs,
        }

    def get_evidence_link(self, link_uid: str) -> EvidenceLink | None:
        """Return evidence link by uid or None (includes retracted links). Phase 3: used when retracting."""
        row = self._conn.execute(
            """SELECT link_uid, claim_uid, span_uid, link_type, strength, notes, rationale, defeater_kind, created_at, created_by_actor_id, source_event_id
               FROM evidence_link WHERE link_uid = ?""",
            (link_uid,),
        ).fetchone()
        if not row:
            return None
        return EvidenceLink(
            link_uid=row[0],
            claim_uid=row[1],
            span_uid=row[2],
            link_type=row[3],
            strength=row[4],
            notes=row[5],
            rationale=row[6],
            defeater_kind=row[7] if len(row) > 7 else None,
            created_at=row[8] if len(row) > 8 else row[7],
            created_by_actor_id=row[9] if len(row) > 9 else row[8],
            source_event_id=row[10] if len(row) > 10 else row[9],
        )

    def _get_links_for_claim(self, claim_uid: str, link_type: str) -> list[EvidenceLink]:
        """Return active (non-retracted) support or challenge links for claim. Phase 3: excludes evidence_link_retraction."""
        cur = self._conn.execute(
            """SELECT el.link_uid, el.claim_uid, el.span_uid, el.link_type, el.strength, el.notes, el.rationale, el.defeater_kind, el.created_at, el.created_by_actor_id, el.source_event_id
               FROM evidence_link el
               LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
               WHERE el.claim_uid = ? AND el.link_type = ? AND r.link_uid IS NULL
               ORDER BY el.created_at ASC""",
            (claim_uid, link_type),
        )
        return [
            EvidenceLink(
                link_uid=r[0],
                claim_uid=r[1],
                span_uid=r[2],
                link_type=r[3],
                strength=r[4],
                notes=r[5],
                rationale=r[6],
                defeater_kind=r[7] if len(r) > 7 else None,
                created_at=r[8] if len(r) > 8 else r[7],
                created_by_actor_id=r[9] if len(r) > 9 else r[8],
                source_event_id=r[10] if len(r) > 10 else r[9],
            )
            for r in cur.fetchall()
        ]

    def get_link_actor_type_breakdown_for_claim(self, claim_uid: str) -> dict[str, int]:
        """Return active link counts by actor_type for this claim.

        Uses evidence_link.source_event_id -> events.event_id to classify links as
        human/tool/system when available.
        """
        cur = self._conn.execute(
            """SELECT LOWER(TRIM(e.actor_type)) AS actor_type, COUNT(*)
               FROM evidence_link el
               LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
               LEFT JOIN events e ON e.event_id = el.source_event_id
               WHERE el.claim_uid = ? AND r.link_uid IS NULL
               GROUP BY LOWER(TRIM(e.actor_type))""",
            (claim_uid,),
        )
        out: dict[str, int] = {}
        for actor_type, count in cur.fetchall():
            key = actor_type if isinstance(actor_type, str) and actor_type.strip() else "unknown"
            out[key] = int(count)
        return out

    def list_graph_links(
        self,
        investigation_uid: str,
        *,
        limit: int,
        after_created_at: str | None = None,
        after_link_uid: str | None = None,
    ) -> list[InvestigationGraphLink]:
        """Return active graph links for an investigation in created_at/link_uid ascending order."""
        sql = """SELECT el.link_uid, el.claim_uid, es.evidence_uid, el.link_type, el.created_at
               FROM evidence_link el
               JOIN claim c ON c.claim_uid = el.claim_uid
               JOIN evidence_span es ON es.span_uid = el.span_uid
               LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
               WHERE c.investigation_uid = ? AND r.link_uid IS NULL"""
        params: list = [investigation_uid]
        if after_created_at is not None:
            cursor_uid = after_link_uid or ""
            sql += " AND (el.created_at > ? OR (el.created_at = ? AND el.link_uid > ?))"
            params.extend([after_created_at, after_created_at, cursor_uid])
        sql += " ORDER BY el.created_at ASC, el.link_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            InvestigationGraphLink(
                link_uid=r[0],
                claim_uid=r[1],
                evidence_uid=r[2],
                link_type=r[3],
                created_at=r[4],
            )
            for r in cur.fetchall()
        ]

    def get_tension(self, tension_uid: str) -> Tension | None:
        """Return tension by uid or None. Phase 11: includes exception_workflow fields when present."""
        row = self._conn.execute(
            """SELECT tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, defeater_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at,
                      assigned_to, due_date, remediation_type
               FROM tension WHERE tension_uid = ?""",
            (tension_uid,),
        ).fetchone()
        if not row:
            return None
        return Tension(
            tension_uid=row[0],
            investigation_uid=row[1],
            claim_a_uid=row[2],
            claim_b_uid=row[3],
            tension_kind=row[4],
            status=row[6],
            notes=row[7],
            created_at=row[8],
            created_by_actor_id=row[9],
            source_event_id=row[10],
            updated_at=row[11],
            assigned_to=row[12],
            due_date=row[13],
            remediation_type=row[14],
            defeater_kind=row[5] if len(row) > 5 else None,
        )

    def get_tensions_for_claim(self, claim_uid: str) -> list[Tension]:
        """Return tensions where claim_uid is claim_a or claim_b. Spec 1.5.2. Phase 11: includes exception_workflow fields."""
        cur = self._conn.execute(
            """SELECT tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, defeater_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at,
                      assigned_to, due_date, remediation_type
               FROM tension WHERE claim_a_uid = ? OR claim_b_uid = ? ORDER BY created_at ASC""",
            (claim_uid, claim_uid),
        )
        return [
            Tension(
                tension_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                tension_kind=r[4],
                status=r[6],
                notes=r[7],
                created_at=r[8],
                created_by_actor_id=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                assigned_to=r[12],
                due_date=r[13],
                remediation_type=r[14],
                defeater_kind=r[5] if len(r) > 5 else None,
            )
            for r in cur.fetchall()
        ]

    def list_tension_suggestions(
        self,
        investigation_uid: str,
        *,
        status: str | None = "pending",
        created_since: str | None = None,
        created_before: str | None = None,
        limit: int = 500,
    ) -> list[TensionSuggestionRow]:
        """Return tension suggestions for an investigation. Phase 7. Default status=pending."""
        sql = """SELECT suggestion_uid, investigation_uid, claim_a_uid, claim_b_uid,
               suggested_tension_kind, confidence, rationale, status, tool_module_id,
               created_at, source_event_id, updated_at, confirmed_tension_uid, dismissed_at
               FROM tension_suggestion WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        if created_since is not None:
            sql += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sql += " AND created_at <= ?"
            params.append(created_before)
        sql += " ORDER BY created_at ASC, suggestion_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            TensionSuggestionRow(
                suggestion_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                suggested_tension_kind=r[4],
                confidence=r[5],
                rationale=r[6],
                status=r[7],
                tool_module_id=r[8],
                created_at=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                confirmed_tension_uid=r[12],
                dismissed_at=r[13],
            )
            for r in cur.fetchall()
        ]

    def list_tension_suggestions_page(
        self,
        investigation_uid: str,
        *,
        status: str | None = "pending",
        limit: int,
        after_created_at: str | None = None,
        after_suggestion_uid: str | None = None,
    ) -> list[TensionSuggestionRow]:
        """Cursor-based tension-suggestion page (created_at/suggestion_uid ascending)."""
        sql = """SELECT suggestion_uid, investigation_uid, claim_a_uid, claim_b_uid,
               suggested_tension_kind, confidence, rationale, status, tool_module_id,
               created_at, source_event_id, updated_at, confirmed_tension_uid, dismissed_at
               FROM tension_suggestion WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        if after_created_at is not None:
            cursor_uid = after_suggestion_uid or ""
            sql += " AND (created_at > ? OR (created_at = ? AND suggestion_uid > ?))"
            params.extend([after_created_at, after_created_at, cursor_uid])
        sql += " ORDER BY created_at ASC, suggestion_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sql, params)
        return [
            TensionSuggestionRow(
                suggestion_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                suggested_tension_kind=r[4],
                confidence=r[5],
                rationale=r[6],
                status=r[7],
                tool_module_id=r[8],
                created_at=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                confirmed_tension_uid=r[12],
                dismissed_at=r[13],
            )
            for r in cur.fetchall()
        ]

    def list_tensions(
        self,
        investigation_uid: str,
        *,
        status: str | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
        limit: int = 500,
    ) -> list[Tension]:
        """Return tensions for an investigation; optional status filter. Phase 5. Phase 11: includes exception_workflow fields."""
        sel = """SELECT tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, defeater_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at,
                         assigned_to, due_date, remediation_type
                   FROM tension WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if status is not None:
            sel += " AND status = ?"
            params.append(status)
        if created_since is not None:
            sel += " AND created_at >= ?"
            params.append(created_since)
        if created_before is not None:
            sel += " AND created_at <= ?"
            params.append(created_before)
        sel += " ORDER BY created_at DESC, tension_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sel, params)
        return [
            Tension(
                tension_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                tension_kind=r[4],
                status=r[6],
                notes=r[7],
                created_at=r[8],
                created_by_actor_id=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                assigned_to=r[12],
                due_date=r[13],
                remediation_type=r[14],
                defeater_kind=r[5] if len(r) > 5 else None,
            )
            for r in cur.fetchall()
        ]

    def list_tensions_page(
        self,
        investigation_uid: str,
        *,
        status: str | None = None,
        limit: int,
        before_created_at: str | None = None,
        before_tension_uid: str | None = None,
    ) -> list[Tension]:
        """Cursor-based tensions page (created_at DESC / tension_uid ASC)."""
        sel = """SELECT tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, defeater_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at,
                         assigned_to, due_date, remediation_type
                   FROM tension WHERE investigation_uid = ?"""
        params: list = [investigation_uid]
        if status is not None:
            sel += " AND status = ?"
            params.append(status)
        if before_created_at is not None:
            cursor_uid = before_tension_uid or ""
            sel += " AND (created_at < ? OR (created_at = ? AND tension_uid > ?))"
            params.extend([before_created_at, before_created_at, cursor_uid])
        sel += " ORDER BY created_at DESC, tension_uid ASC LIMIT ?"
        params.append(min(max(1, limit), MAX_LIST_LIMIT))
        cur = self._conn.execute(sel, params)
        return [
            Tension(
                tension_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                tension_kind=r[4],
                status=r[6],
                notes=r[7],
                created_at=r[8],
                created_by_actor_id=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                assigned_to=r[12],
                due_date=r[13],
                remediation_type=r[14],
                defeater_kind=r[5] if len(r) > 5 else None,
            )
            for r in cur.fetchall()
        ]

    def list_tensions_overdue(self, investigation_uid: str, limit: int = 500) -> list[Tension]:
        """Return tensions with due_date in the past and status not RESOLVED. Phase D.1 (exception workflow)."""
        sel = """SELECT tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, defeater_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at,
                         assigned_to, due_date, remediation_type
                   FROM tension
                   WHERE investigation_uid = ? AND due_date IS NOT NULL AND due_date < date('now') AND status != 'RESOLVED'
                   ORDER BY due_date ASC
                   LIMIT ?"""
        cur = self._conn.execute(sel, (investigation_uid, limit))
        return [
            Tension(
                tension_uid=r[0],
                investigation_uid=r[1],
                claim_a_uid=r[2],
                claim_b_uid=r[3],
                tension_kind=r[4],
                status=r[6],
                notes=r[7],
                created_at=r[8],
                created_by_actor_id=r[9],
                source_event_id=r[10],
                updated_at=r[11],
                assigned_to=r[12],
                due_date=r[13],
                remediation_type=r[14],
                defeater_kind=r[5] if len(r) > 5 else None,
            )
            for r in cur.fetchall()
        ]

    def get_tension_suggestion(self, suggestion_uid: str) -> TensionSuggestionRow | None:
        """Return one tension suggestion by uid. Phase 7."""
        row = self._conn.execute(
            """SELECT suggestion_uid, investigation_uid, claim_a_uid, claim_b_uid,
               suggested_tension_kind, confidence, rationale, status, tool_module_id,
               created_at, source_event_id, updated_at, confirmed_tension_uid, dismissed_at
               FROM tension_suggestion WHERE suggestion_uid = ?""",
            (suggestion_uid,),
        ).fetchone()
        if not row:
            return None
        return TensionSuggestionRow(
            suggestion_uid=row[0],
            investigation_uid=row[1],
            claim_a_uid=row[2],
            claim_b_uid=row[3],
            suggested_tension_kind=row[4],
            confidence=row[5],
            rationale=row[6],
            status=row[7],
            tool_module_id=row[8],
            created_at=row[9],
            source_event_id=row[10],
            updated_at=row[11],
            confirmed_tension_uid=row[12],
            dismissed_at=row[13],
        )

    def list_assertions_for_claim(self, claim_uid: str) -> list[ClaimAssertion]:
        """Return assertions for the claim. For MES confidence check."""
        cur = self._conn.execute(
            """SELECT assertion_uid, claim_uid, asserted_at, actor_type, actor_id, assertion_mode, confidence, justification, source_event_id
               FROM claim_assertion WHERE claim_uid = ? ORDER BY asserted_at ASC""",
            (claim_uid,),
        )
        return [
            ClaimAssertion(
                assertion_uid=r[0],
                claim_uid=r[1],
                asserted_at=r[2],
                actor_type=r[3],
                actor_id=r[4],
                assertion_mode=r[5],
                confidence=r[6],
                justification=r[7],
                source_event_id=r[8],
            )
            for r in cur.fetchall()
        ]
