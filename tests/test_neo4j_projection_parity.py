from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from chronicle.store.neo4j_export import export_project_to_neo4j_csv
from chronicle.store.neo4j_sync import (
    _claim_content_hash,
    _evidence_link_select_sql,
    _evidence_link_select_with_claim_sql,
)
from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.session import ChronicleSession


def _seed_project(project_path: Path) -> None:
    create_project(project_path)
    with ChronicleSession(project_path) as session:
        _, inv_a = session.create_investigation("Parity A", actor_id="test", actor_type="tool")
        _, ev_a = session.ingest_evidence(
            inv_a,
            b"shared evidence bytes",
            "text/plain",
            original_filename="shared_a.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_a = session.anchor_span(
            inv_a,
            ev_a,
            "text_offset",
            {"start_char": 0, "end_char": 6},
            quote="shared",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_a = session.propose_claim(
            inv_a,
            "Repeated claim text for dedupe parity.",
            actor_id="test",
            actor_type="tool",
        )
        session.link_support(inv_a, span_a, claim_a, actor_id="test", actor_type="tool")
        session.link_support(inv_a, span_a, claim_a, actor_id="test", actor_type="tool")
        session.link_challenge(inv_a, span_a, claim_a, actor_id="test", actor_type="tool")

        _, inv_b = session.create_investigation("Parity B", actor_id="test", actor_type="tool")
        _, ev_b = session.ingest_evidence(
            inv_b,
            b"shared evidence bytes",
            "text/plain",
            original_filename="shared_b.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_b = session.anchor_span(
            inv_b,
            ev_b,
            "text_offset",
            {"start_char": 0, "end_char": 6},
            quote="shared",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_b = session.propose_claim(
            inv_b,
            "Repeated claim text for dedupe parity.",
            actor_id="test",
            actor_type="tool",
        )
        session.link_support(inv_b, span_b, claim_b, actor_id="test", actor_type="tool")


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_non_dedupe_export_links_match_sync_source_rows(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    _seed_project(project_path)
    csv_dir = tmp_path / "csv"
    export_project_to_neo4j_csv(project_path, csv_dir)

    export_links = _load_csv(csv_dir / "links.csv")
    export_set = {
        (row["link_uid"], row["claim_uid"], row["span_uid"], row["link_type"])
        for row in export_links
    }

    conn = sqlite3.connect(str(project_path / CHRONICLE_DB))
    try:
        expected: set[tuple[str, str, str, str]] = set()
        for span_uid, claim_uid, link_uid, _source_event_id, _rationale in conn.execute(
            _evidence_link_select_sql(conn, link_type="SUPPORTS")
        ).fetchall():
            expected.add((str(link_uid), str(claim_uid), str(span_uid), "SUPPORTS"))
        for span_uid, claim_uid, link_uid, _source_event_id, _rationale in conn.execute(
            _evidence_link_select_sql(conn, link_type="CHALLENGES")
        ).fetchall():
            expected.add((str(link_uid), str(claim_uid), str(span_uid), "CHALLENGES"))
    finally:
        conn.close()

    assert export_set == expected


def test_dedupe_mode_lineage_hash_semantics_are_explicit(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    _seed_project(project_path)
    csv_dir = tmp_path / "csv"
    export_project_to_neo4j_csv(project_path, csv_dir)

    export_claim_rows = _load_csv(csv_dir / "claims.csv")
    export_claim_uids = {row["claim_uid"] for row in export_claim_rows}

    conn = sqlite3.connect(str(project_path / CHRONICLE_DB))
    try:
        claim_rows = conn.execute(
            "SELECT investigation_uid, claim_uid, claim_text FROM claim ORDER BY claim_uid"
        ).fetchall()
        contains_claim_lineage = {
            (str(investigation_uid), str(claim_uid), _claim_content_hash(str(claim_text)))
            for investigation_uid, claim_uid, claim_text in claim_rows
        }
        claim_hashes = {claim_hash for _inv, _uid, claim_hash in contains_claim_lineage}

        evidence_rows = conn.execute(
            "SELECT investigation_uid, evidence_uid, content_hash FROM evidence_item ORDER BY evidence_uid"
        ).fetchall()
        contains_evidence_lineage = {
            (str(investigation_uid), str(evidence_uid), str(content_hash))
            for investigation_uid, evidence_uid, content_hash in evidence_rows
        }

        dedupe_support_targets = {
            (str(link_uid), _claim_content_hash(str(claim_text)), str(span_uid), "SUPPORTS")
            for span_uid, _claim_uid, link_uid, _source_event_id, _rationale, claim_text in conn.execute(
                _evidence_link_select_with_claim_sql(conn, link_type="SUPPORTS")
            ).fetchall()
        }
        dedupe_challenge_targets = {
            (str(link_uid), _claim_content_hash(str(claim_text)), str(span_uid), "CHALLENGES")
            for span_uid, _claim_uid, link_uid, _source_event_id, _rationale, claim_text in conn.execute(
                _evidence_link_select_with_claim_sql(conn, link_type="CHALLENGES")
            ).fetchall()
        }
    finally:
        conn.close()

    assert len(claim_hashes) < len(claim_rows)
    assert len({content_hash for _inv, _uid, content_hash in contains_evidence_lineage}) < len(
        evidence_rows
    )

    assert export_claim_uids == {str(claim_uid) for _inv, claim_uid, _text in claim_rows}
    assert export_claim_uids != claim_hashes
    assert all(len(uid) == 64 for uid in claim_hashes)
    assert all(ch in "0123456789abcdef" for uid in claim_hashes for ch in uid)

    export_link_rows = _load_csv(csv_dir / "links.csv")
    export_support_links = {
        (row["link_uid"], row["claim_uid"], row["span_uid"], row["link_type"])
        for row in export_link_rows
        if row["link_type"] == "SUPPORTS"
    }
    export_challenge_links = {
        (row["link_uid"], row["claim_uid"], row["span_uid"], row["link_type"])
        for row in export_link_rows
        if row["link_type"] == "CHALLENGES"
    }

    assert {row[0] for row in export_support_links} == {row[0] for row in dedupe_support_targets}
    assert {row[0] for row in export_challenge_links} == {
        row[0] for row in dedupe_challenge_targets
    }
    assert all(row[1] in claim_hashes for row in dedupe_support_targets)
    assert all(row[1] in claim_hashes for row in dedupe_challenge_targets)
