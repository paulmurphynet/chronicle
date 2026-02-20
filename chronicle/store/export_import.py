"""Export/import .chronicle (ZIP + manifest). Spec evidence.md 4.1.1."""

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle import log
from chronicle.core.events import Event
from chronicle.core.policy import (
    POLICY_FILENAME,
    get_policy_publication_summary,
    load_policy_profile,
)
from chronicle.store.evidence_store import EVIDENCE_DIR
from chronicle.store.project import CHRONICLE_DB
from chronicle.store.read_model import apply_event
from chronicle.store.schema import (
    ensure_evidence_provenance_column,
    ensure_evidence_redaction_columns,
    init_event_store_schema,
    init_read_model_schema,
)

CHRONICLE_FORMAT_VERSION = 1
CHRONICLE_EXT = ".chronicle"


def _sha256_file(path: Path) -> str:
    """Return SHA-256 digest for a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _verify_importable_archive(chronicle_path: Path) -> None:
    """Block import when archive integrity checks fail."""
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    results = verify_chronicle_file(chronicle_path, run_invariants=False)
    failures = [f"{name}: {detail}" for name, passed, detail in results if not passed]
    if failures:
        msg = "; ".join(failures[:3])
        if len(failures) > 3:
            msg = f"{msg}; ..."
        raise ValueError(f"Import blocked: .chronicle verification failed ({msg})")


def _merge_copy_evidence_files(src_evidence: Path, target_evidence: Path) -> None:
    """Copy evidence files without overwriting existing different bytes."""
    src_root = src_evidence.resolve()
    target_root = target_evidence.resolve()
    for f in src_evidence.rglob("*"):
        if not f.is_file():
            continue
        rel = f.resolve().relative_to(src_root)
        dest = (target_evidence / rel).resolve()
        try:
            dest.relative_to(target_root)
        except ValueError as exc:
            raise ValueError(f"Import blocked: evidence path escapes target: {rel}") from exc
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if _sha256_file(dest) != _sha256_file(f):
                raise ValueError(
                    f"Import blocked: evidence file conflict for {rel}; target file differs from archive"
                )
            continue
        shutil.copy2(f, dest)


def _row_to_event(row: tuple) -> Event:
    """Build Event from DB row (events table column order)."""
    return Event(
        event_id=row[0],
        event_type=row[1],
        occurred_at=row[2],
        recorded_at=row[3],
        investigation_uid=row[4],
        subject_uid=row[5],
        actor_type=row[6],
        actor_id=row[7],
        workspace=row[8],
        policy_profile_id=row[9],
        correlation_id=row[10],
        causation_id=row[11],
        envelope_version=row[12],
        payload_version=row[13],
        payload=json.loads(row[14]) if isinstance(row[14], str) else row[14],
        idempotency_key=row[15],
        prev_event_hash=row[16],
        event_hash=row[17],
    )


def export_investigation(
    project_dir: Path,
    investigation_uid: str,
    output_path: Path,
) -> Path:
    """Export a single investigation to a .chronicle file (ZIP with db subset, evidence, manifest). Read-only. Spec 4.1.1."""
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    if output_path.suffix != CHRONICLE_EXT:
        output_path = output_path.with_suffix(CHRONICLE_EXT)

    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")

    conn = sqlite3.connect(str(db_path))
    try:
        # Load events for this investigation in order
        # Order by rowid so replay matches append order (avoids FK failures when
        # recorded_at ties and event_id order differs from insertion order).
        cur = conn.execute(
            """SELECT event_id, event_type, occurred_at, recorded_at,
                      investigation_uid, subject_uid, actor_type, actor_id, workspace,
                      policy_profile_id, correlation_id, causation_id,
                      envelope_version, payload_version, payload,
                      idempotency_key, prev_event_hash, event_hash
               FROM events WHERE investigation_uid = ? ORDER BY rowid ASC""",
            (investigation_uid,),
        )
        rows = cur.fetchall()
        if not rows:
            raise ValueError(f"No events found for investigation {investigation_uid}")

        redacted_evidence = []
        redacted_uids = set()
        # Ensure redaction and provenance columns exist (Phase C.1, E2.3) so we can query evidence
        ensure_evidence_redaction_columns(conn)
        ensure_evidence_provenance_column(conn)
        # Get investigation title and evidence URIs from read model (we need to query current read model)
        inv_row = conn.execute(
            "SELECT title FROM investigation WHERE investigation_uid = ?", (investigation_uid,)
        ).fetchone()
        title = inv_row[0] if inv_row else investigation_uid
        ev_cur = conn.execute(
            "SELECT evidence_uid, uri FROM evidence_item WHERE investigation_uid = ?",
            (investigation_uid,),
        )
        evidence_uris = [(r[0], r[1]) for r in ev_cur.fetchall()]
        # Phase C.1: list redacted evidence (strip from export, flag in manifest)
        try:
            redacted_cur = conn.execute(
                """SELECT evidence_uid, redaction_reason, redaction_at FROM evidence_item
                   WHERE investigation_uid = ? AND redaction_reason IS NOT NULL AND redaction_reason != ''""",
                (investigation_uid,),
            )
            redacted_evidence = [
                {"evidence_uid": r[0], "redaction_reason": r[1], "redaction_at": r[2]}
                for r in redacted_cur.fetchall()
            ]
        except sqlite3.OperationalError:
            redacted_evidence = []
        redacted_uids = {r["evidence_uid"] for r in redacted_evidence}
    finally:
        conn.close()

    # Build temp export dir
    import tempfile

    with tempfile.TemporaryDirectory(prefix="chronicle_export_") as tmp:
        tmp_path = Path(tmp)
        export_db = tmp_path / CHRONICLE_DB
        evidence_out = tmp_path / EVIDENCE_DIR
        evidence_out.mkdir(parents=True, exist_ok=True)

        # Create new DB with schema and only this investigation's events (replay to build read model)
        export_conn = sqlite3.connect(str(export_db))
        export_conn.execute("PRAGMA foreign_keys = ON")
        init_event_store_schema(export_conn)
        init_read_model_schema(export_conn)
        for row in rows:
            event = _row_to_event(row)
            # Insert event then run projection
            payload_json = (
                json.dumps(event.payload) if isinstance(event.payload, dict) else event.payload
            )
            export_conn.execute(
                """INSERT INTO events (
                    event_id, event_type, occurred_at, recorded_at,
                    investigation_uid, subject_uid, actor_type, actor_id, workspace,
                    policy_profile_id, correlation_id, causation_id,
                    envelope_version, payload_version, payload,
                    idempotency_key, prev_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.event_type,
                    event.occurred_at,
                    event.recorded_at,
                    event.investigation_uid,
                    event.subject_uid,
                    event.actor_type,
                    event.actor_id,
                    event.workspace,
                    event.policy_profile_id,
                    event.correlation_id,
                    event.causation_id,
                    event.envelope_version,
                    event.payload_version,
                    payload_json,
                    event.idempotency_key,
                    event.prev_event_hash,
                    event.event_hash,
                ),
            )
            apply_event(export_conn, event)
        export_conn.commit()
        export_conn.close()

        # Copy evidence files (path traversal safe: only copy if src under project_dir). Phase C.1: skip redacted.
        project_resolved = project_dir.resolve()
        for ev_uid, uri in evidence_uris:
            if ev_uid in redacted_uids:
                continue  # strip redacted evidence from export
            src = (project_dir / uri).resolve()
            try:
                src.relative_to(project_resolved)
            except ValueError:
                continue  # skip URIs that escape project
            if src.is_file():
                dst = tmp_path / uri
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Content hash manifest from export db (evidence_item has content_hash from projection)
        content_hash_manifest = {}
        export_conn = sqlite3.connect(str(export_db))
        for ev_uid, _ in evidence_uris:
            r = export_conn.execute(
                "SELECT content_hash FROM evidence_item WHERE evidence_uid = ?", (ev_uid,)
            ).fetchone()
            if r:
                content_hash_manifest[ev_uid] = r[0]
        export_conn.close()

        # Manifest (Phase 9: built_under policy for policy compatibility view)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest: dict[str, Any] = {
            "format_version": CHRONICLE_FORMAT_VERSION,
            "investigation_uid": investigation_uid,
            "title": title,
            "exported_at": now,
        }
        try:
            export_policy = load_policy_profile(project_dir / POLICY_FILENAME)
            manifest["built_under_policy_id"] = export_policy.profile_id
            try:
                import hashlib

                manifest["built_under_policy_version"] = hashlib.sha256(
                    json.dumps(export_policy.to_dict(), sort_keys=True).encode()
                ).hexdigest()[:16]
            except Exception:
                pass
            manifest["policy_summary"] = get_policy_publication_summary(export_policy)
        except Exception:
            pass
        if redacted_evidence:
            manifest["redacted_evidence"] = redacted_evidence
        if content_hash_manifest:
            manifest["content_hash_manifest"] = content_hash_manifest
        (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Zip to output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in tmp_path.rglob("*"):
                if f.is_file():
                    arcname = f.relative_to(tmp_path)
                    zf.write(f, arcname)

    return output_path


def _minimal_export_needed_uids(
    conn: sqlite3.Connection, investigation_uid: str, claim_uid: str
) -> tuple[set[str], list[tuple[str, str]]]:
    """Return (needed_subject_uids, evidence_uris) for a minimal export for one claim. Raises ValueError if claim not found."""
    cur = conn.execute(
        "SELECT claim_uid, investigation_uid FROM claim WHERE claim_uid = ? AND investigation_uid = ?",
        (claim_uid, investigation_uid),
    )
    if cur.fetchone() is None:
        raise ValueError(f"Claim {claim_uid} not found in investigation {investigation_uid}")
    needed = {investigation_uid, claim_uid}
    # Links (support/challenge) for this claim -> span_uids, link_uids; then evidence_uid per span
    cur = conn.execute(
        """SELECT el.link_uid, el.span_uid FROM evidence_link el
           LEFT JOIN evidence_link_retraction r ON el.link_uid = r.link_uid
           WHERE el.claim_uid = ? AND r.link_uid IS NULL""",
        (claim_uid,),
    )
    link_span = cur.fetchall()
    evidence_uids = set()
    for _link_uid, span_uid in link_span:
        needed.add(span_uid)
        row = conn.execute(
            "SELECT evidence_uid FROM evidence_span WHERE span_uid = ?", (span_uid,)
        ).fetchone()
        if row:
            evidence_uids.add(row[0])
    needed.update(r[0] for r in link_span)  # link_uids
    needed.update(evidence_uids)
    # Tensions involving this claim
    cur = conn.execute(
        "SELECT tension_uid FROM tension WHERE claim_a_uid = ? OR claim_b_uid = ?",
        (claim_uid, claim_uid),
    )
    for row in cur.fetchall():
        needed.add(row[0])
    # Evidence URIs only for evidence we need
    evidence_uris = []
    for ev_uid in evidence_uids:
        r = conn.execute(
            "SELECT evidence_uid, uri FROM evidence_item WHERE evidence_uid = ?",
            (ev_uid,),
        ).fetchone()
        if r:
            evidence_uris.append((r[0], r[1]))
    return needed, evidence_uris


def export_minimal_for_claim(
    project_dir: Path,
    investigation_uid: str,
    claim_uid: str,
    output_path: Path,
) -> Path:
    """Export a minimal .chronicle containing only one claim and its evidence/links/tensions so the verifier can validate it. P2.2.2."""
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    if output_path.suffix != CHRONICLE_EXT:
        output_path = output_path.with_suffix(CHRONICLE_EXT)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")
    conn = sqlite3.connect(str(db_path))
    try:
        needed_uids, evidence_uris = _minimal_export_needed_uids(conn, investigation_uid, claim_uid)
        cur = conn.execute(
            """SELECT event_id, event_type, occurred_at, recorded_at,
                      investigation_uid, subject_uid, actor_type, actor_id, workspace,
                      policy_profile_id, correlation_id, causation_id,
                      envelope_version, payload_version, payload,
                      idempotency_key, prev_event_hash, event_hash
               FROM events WHERE investigation_uid = ? ORDER BY rowid ASC""",
            (investigation_uid,),
        )
        all_rows = cur.fetchall()
        rows = [r for r in all_rows if r[5] in needed_uids]  # subject_uid is index 5
        if not rows:
            raise ValueError(
                f"No events found for claim {claim_uid} in investigation {investigation_uid}"
            )
        ensure_evidence_redaction_columns(conn)
        ensure_evidence_provenance_column(conn)
        inv_row = conn.execute(
            "SELECT title FROM investigation WHERE investigation_uid = ?", (investigation_uid,)
        ).fetchone()
        title = inv_row[0] if inv_row else investigation_uid
        redacted_evidence = []
        try:
            redacted_cur = conn.execute(
                """SELECT evidence_uid, redaction_reason, redaction_at FROM evidence_item
                   WHERE investigation_uid = ? AND redaction_reason IS NOT NULL AND redaction_reason != ''""",
                (investigation_uid,),
            )
            redacted_evidence = [
                {"evidence_uid": r[0], "redaction_reason": r[1], "redaction_at": r[2]}
                for r in redacted_cur.fetchall()
            ]
        except sqlite3.OperationalError:
            pass
        redacted_uids = {r["evidence_uid"] for r in redacted_evidence}
        evidence_uris = [
            (ev_uid, uri) for ev_uid, uri in evidence_uris if ev_uid not in redacted_uids
        ]
    finally:
        conn.close()

    with tempfile.TemporaryDirectory(prefix="chronicle_export_") as tmp:
        tmp_path = Path(tmp)
        export_db = tmp_path / CHRONICLE_DB
        evidence_out = tmp_path / EVIDENCE_DIR
        evidence_out.mkdir(parents=True, exist_ok=True)
        export_conn = sqlite3.connect(str(export_db))
        export_conn.execute("PRAGMA foreign_keys = ON")
        init_event_store_schema(export_conn)
        init_read_model_schema(export_conn)
        for row in rows:
            event = _row_to_event(row)
            payload_json = (
                json.dumps(event.payload) if isinstance(event.payload, dict) else event.payload
            )
            export_conn.execute(
                """INSERT INTO events (
                    event_id, event_type, occurred_at, recorded_at,
                    investigation_uid, subject_uid, actor_type, actor_id, workspace,
                    policy_profile_id, correlation_id, causation_id,
                    envelope_version, payload_version, payload,
                    idempotency_key, prev_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.event_type,
                    event.occurred_at,
                    event.recorded_at,
                    event.investigation_uid,
                    event.subject_uid,
                    event.actor_type,
                    event.actor_id,
                    event.workspace,
                    event.policy_profile_id,
                    event.correlation_id,
                    event.causation_id,
                    event.envelope_version,
                    event.payload_version,
                    payload_json,
                    event.idempotency_key,
                    event.prev_event_hash,
                    event.event_hash,
                ),
            )
            apply_event(export_conn, event)
        export_conn.commit()
        project_resolved = project_dir.resolve()
        for _ev_uid, uri in evidence_uris:
            src = (project_dir / uri).resolve()
            try:
                src.relative_to(project_resolved)
            except ValueError:
                continue
            if src.is_file():
                dst = tmp_path / uri
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        content_hash_manifest = {}
        for ev_uid, _ in evidence_uris:
            r = export_conn.execute(
                "SELECT content_hash FROM evidence_item WHERE evidence_uid = ?", (ev_uid,)
            ).fetchone()
            if r:
                content_hash_manifest[ev_uid] = r[0]
        export_conn.close()
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = {
            "format_version": CHRONICLE_FORMAT_VERSION,
            "investigation_uid": investigation_uid,
            "title": title,
            "exported_at": now,
            "minimal_claim_uid": claim_uid,
        }
        try:
            export_policy = load_policy_profile(project_dir / POLICY_FILENAME)
            manifest["built_under_policy_id"] = export_policy.profile_id
            try:
                import hashlib

                manifest["built_under_policy_version"] = hashlib.sha256(
                    json.dumps(export_policy.to_dict(), sort_keys=True).encode()
                ).hexdigest()[:16]
            except Exception:
                pass
            manifest["policy_summary"] = get_policy_publication_summary(export_policy)
        except Exception:
            pass
        if redacted_evidence:
            manifest["redacted_evidence"] = redacted_evidence
        if content_hash_manifest:
            manifest["content_hash_manifest"] = content_hash_manifest
        (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in tmp_path.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp_path))
    return output_path


def import_investigation(chronicle_path: Path, target_dir: Path) -> None:
    """Import a .chronicle file into target_dir. If target has no chronicle.db, extract as fresh project; else merge events and evidence. Spec 4.1.1."""
    chronicle_path = Path(chronicle_path)
    target_dir = Path(target_dir)
    log.info("Importing %s into %s", chronicle_path.name, target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_db = target_dir / CHRONICLE_DB
    target_evidence = target_dir / EVIDENCE_DIR

    if not chronicle_path.is_file() or chronicle_path.suffix != CHRONICLE_EXT:
        raise FileNotFoundError(f"Not a .chronicle file: {chronicle_path}")
    _verify_importable_archive(chronicle_path)

    with zipfile.ZipFile(chronicle_path, "r") as zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            raise ValueError("Invalid .chronicle: missing manifest.json")
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        inv_uid = manifest.get("investigation_uid")
        if not inv_uid:
            raise ValueError("Invalid manifest: missing investigation_uid")

        if not target_db.exists():
            # Fresh import: extract all (reject absolute and path-traversal names)
            target_resolved = target_dir.resolve()
            for name in names:
                if (
                    name.startswith("__")
                    or ".." in name
                    or name.startswith("/")
                    or (name.startswith("\\") and len(name) > 1)
                ):
                    continue
                dest = (target_dir / name).resolve()
                try:
                    dest.relative_to(target_resolved)
                except ValueError:
                    continue
                if name.endswith("/"):
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))
            return

        # Merge: extract to temp, replay events into target, copy evidence
        import tempfile

        with tempfile.TemporaryDirectory(prefix="chronicle_import_") as tmp:
            tmp_path = Path(tmp)
            tmp_resolved = tmp_path.resolve()
            for name in names:
                if (
                    name.startswith("__")
                    or ".." in name
                    or name.startswith("/")
                    or (name.startswith("\\") and len(name) > 1)
                ):
                    continue
                dest = (tmp_path / name).resolve()
                try:
                    dest.relative_to(tmp_resolved)
                except ValueError:
                    continue
                if name.endswith("/"):
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))

            source_db = tmp_path / CHRONICLE_DB
            if not source_db.is_file():
                raise ValueError("Invalid .chronicle: missing chronicle.db")

            source_conn = sqlite3.connect(str(source_db))
            cur = source_conn.execute(
                """SELECT event_id, event_type, occurred_at, recorded_at,
                          investigation_uid, subject_uid, actor_type, actor_id, workspace,
                          policy_profile_id, correlation_id, causation_id,
                          envelope_version, payload_version, payload,
                          idempotency_key, prev_event_hash, event_hash
                   FROM events ORDER BY rowid ASC"""
            )
            events = [_row_to_event(r) for r in cur.fetchall()]
            source_conn.close()

            from chronicle.store.sqlite_event_store import SqliteEventStore

            target_store = SqliteEventStore(target_db, run_projection=True)
            target_store._connection()
            skipped_duplicates = 0
            try:
                for event in events:
                    try:
                        target_store.append(event)
                    except sqlite3.IntegrityError:
                        # Merge import is idempotent by event_id. Skip duplicate events and
                        # continue replaying remaining events so mixed duplicate/new imports
                        # do not stop at the first duplicate.
                        skipped_duplicates += 1
            finally:
                target_store.close()
            if skipped_duplicates:
                log.info(
                    "Import merge skipped %d duplicate event(s) while replaying %d event(s)",
                    skipped_duplicates,
                    len(events),
                )

            # Copy evidence files from temp to target without overwriting conflicts.
            src_evidence = tmp_path / EVIDENCE_DIR
            if src_evidence.is_dir():
                target_evidence.mkdir(parents=True, exist_ok=True)
                _merge_copy_evidence_files(src_evidence, target_evidence)
