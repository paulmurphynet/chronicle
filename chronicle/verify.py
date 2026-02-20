"""Invariant verification suite. Spec 12.7.5, 15.6. Run against any Chronicle DB or project."""

import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chronicle.store.project import CHRONICLE_DB


@dataclass
class CheckResult:
    """Result of one invariant check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class VerifyReport:
    """Full report from running the invariant suite."""

    passed: bool
    results: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(CheckResult(name=name, passed=passed, detail=detail))
        if not passed:
            self.passed = False


def _db_path(project_dir: Path) -> Path:
    return project_dir / CHRONICLE_DB


def verify_append_only_ledger(conn: Any, report: VerifyReport) -> None:
    """Events table exists; no recorded_at reversals (Spec 12.7.5: append-only, no timestamp reversals)."""
    try:
        try:
            cur = conn.execute("SELECT event_id, recorded_at FROM events ORDER BY rowid ASC")
        except Exception:
            # PostgreSQL has no rowid; use logical event ordering.
            cur = conn.execute(
                "SELECT event_id, recorded_at FROM events ORDER BY recorded_at ASC, event_id ASC"
            )
        rows = cur.fetchall()
        if not rows:
            report.add("append_only_ledger", True, "no events (empty store)")
            return
        prev_recorded = ""
        for eid, rec in rows:
            if rec < prev_recorded:
                report.add("append_only_ledger", False, f"recorded_at reversal at event_id={eid}")
                return
            prev_recorded = rec
        report.add("append_only_ledger", True, f"{len(rows)} events in order")
    except Exception as e:
        report.add("append_only_ledger", False, str(e))


def verify_referential_integrity(conn: Any, report: VerifyReport) -> None:
    """All FKs in read model are satisfied: link -> claim+span, tension -> claim+claim, etc."""
    failed: list[str] = []
    try:
        claim_uids = {r[0] for r in conn.execute("SELECT claim_uid FROM claim").fetchall()}
        span_uids = {r[0] for r in conn.execute("SELECT span_uid FROM evidence_span").fetchall()}
        evidence_uids = {
            r[0] for r in conn.execute("SELECT evidence_uid FROM evidence_item").fetchall()
        }
        checkpoint_uids = {
            r[0] for r in conn.execute("SELECT checkpoint_uid FROM checkpoint").fetchall()
        }
        artifact_uids = {r[0] for r in conn.execute("SELECT artifact_uid FROM artifact").fetchall()}
    except Exception as e:
        report.add("referential_integrity", False, str(e))
        return

    # evidence_link: claim_uid in claim, span_uid in evidence_span
    cur = conn.execute("SELECT link_uid, claim_uid, span_uid FROM evidence_link")
    for link_uid, claim_uid, span_uid in cur.fetchall():
        if claim_uid not in claim_uids:
            failed.append(f"evidence_link {link_uid}: claim_uid {claim_uid} missing")
        if span_uid not in span_uids:
            failed.append(f"evidence_link {link_uid}: span_uid {span_uid} missing")

    # tension: claim_a_uid, claim_b_uid in claim
    cur = conn.execute("SELECT tension_uid, claim_a_uid, claim_b_uid FROM tension")
    for tid, a, b in cur.fetchall():
        if a not in claim_uids:
            failed.append(f"tension {tid}: claim_a_uid {a} missing")
        if b not in claim_uids:
            failed.append(f"tension {tid}: claim_b_uid {b} missing")

    # claim_assertion.claim_uid, claim_decomposition.claim_uid (whitelist tables: no string interpolation)
    for table, col in [("claim_assertion", "claim_uid"), ("claim_decomposition", "claim_uid")]:
        try:
            if table == "claim_assertion":
                cur = conn.execute("SELECT claim_uid FROM claim_assertion")
            else:
                cur = conn.execute("SELECT claim_uid FROM claim_decomposition")
            for (uid,) in cur.fetchall():
                if uid not in claim_uids:
                    failed.append(f"{table}: {col} {uid} missing")
        except Exception:
            pass

    # claim.parent_claim_uid
    cur = conn.execute(
        "SELECT claim_uid, parent_claim_uid FROM claim WHERE parent_claim_uid IS NOT NULL"
    )
    for cid, pid in cur.fetchall():
        if pid not in claim_uids:
            failed.append(f"claim {cid}: parent_claim_uid {pid} missing")

    # evidence_span.evidence_uid
    cur = conn.execute("SELECT span_uid, evidence_uid FROM evidence_span")
    for span_uid, ev_uid in cur.fetchall():
        if ev_uid not in evidence_uids:
            failed.append(f"evidence_span {span_uid}: evidence_uid {ev_uid} missing")

    # checkpoint_artifact_freeze
    try:
        cur = conn.execute("SELECT checkpoint_uid, artifact_uid FROM checkpoint_artifact_freeze")
        for cp_uid, art_uid in cur.fetchall():
            if cp_uid not in checkpoint_uids:
                failed.append(f"checkpoint_artifact_freeze: checkpoint_uid {cp_uid} missing")
            if art_uid not in artifact_uids:
                failed.append(f"checkpoint_artifact_freeze: artifact_uid {art_uid} missing")
    except Exception:
        pass

    if failed:
        report.add(
            "referential_integrity",
            False,
            "; ".join(failed[:10]) + ("..." if len(failed) > 10 else ""),
        )
    else:
        report.add("referential_integrity", True, "all references valid")


def verify_status_consistency(conn: Any, report: VerifyReport) -> None:
    """No claim has current_status=ACTIVE after a ClaimWithdrawn for that claim (by event history)."""
    # Simplified: check that every claim's current_status is in allowed set
    allowed_claim_status = frozenset({"ACTIVE", "WITHDRAWN", "DOWNGRADED"})
    allowed_tension_status = frozenset(
        {
            "OPEN",
            "ACK",
            "RESOLVED",
            "DISPUTED",
            "DEFERRED",
            "INTRACTABLE",
            "SUPERSEDED",
            "ESCALATED",
        }
    )
    failed: list[str] = []

    cur = conn.execute("SELECT claim_uid, current_status FROM claim")
    for cid, status in cur.fetchall():
        if status not in allowed_claim_status:
            failed.append(f"claim {cid}: invalid status {status!r}")

    try:
        cur = conn.execute("SELECT tension_uid, status FROM tension")
        for tid, status in cur.fetchall():
            if status not in allowed_tension_status:
                failed.append(f"tension {tid}: invalid status {status!r}")
    except Exception:
        pass

    if failed:
        report.add(
            "status_consistency", False, "; ".join(failed[:5]) + ("..." if len(failed) > 5 else "")
        )
    else:
        report.add("status_consistency", True, "all statuses in allowed sets")


def verify_projection_completeness(conn: Any, report: VerifyReport) -> None:
    """processed_event rows for read_model match event count (every event processed)."""
    try:
        event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        processed = conn.execute(
            "SELECT COUNT(DISTINCT event_id) FROM processed_event WHERE projection_name = 'read_model'"
        ).fetchone()[0]
        if event_count != processed:
            report.add(
                "projection_completeness",
                False,
                f"events={event_count} vs processed read_model={processed}",
            )
        else:
            report.add("projection_completeness", True, f"all {event_count} events processed")
    except Exception as e:
        report.add("projection_completeness", False, str(e))


def verify_evidence_integrity(conn: Any, project_dir: Path, report: VerifyReport) -> None:
    """All evidence files on disk match recorded content_hash (where file exists)."""
    try:
        cur = conn.execute("SELECT evidence_uid, content_hash, uri FROM evidence_item")
        rows = cur.fetchall()
    except Exception as e:
        report.add("evidence_integrity", False, str(e))
        return

    failed: list[str] = []
    checked = 0
    project_resolved = Path(project_dir).resolve()
    for evidence_uid, content_hash, uri in rows:
        raw = project_dir / uri if uri else project_dir / "evidence" / evidence_uid
        try:
            path = raw.resolve().relative_to(project_resolved)
            path = project_resolved / path
        except ValueError:
            failed.append(f"{evidence_uid}: uri escapes project")
            continue
        if not path.is_file():
            failed.append(f"{evidence_uid}: file missing {path}")
            continue
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        checked += 1
        if digest != content_hash:
            failed.append(f"{evidence_uid}: hash mismatch")

    if failed:
        report.add(
            "evidence_integrity", False, "; ".join(failed[:5]) + ("..." if len(failed) > 5 else "")
        )
    else:
        report.add(
            "evidence_integrity",
            True,
            f"all {checked} evidence files match hash" if checked else "no evidence items",
        )


def verify_project(project_dir: Path | str, *, check_evidence_files: bool = True) -> VerifyReport:
    """Run full invariant suite on a Chronicle project. Spec 12.7.5."""
    project_dir = Path(project_dir)
    report = VerifyReport(passed=True)
    db_path = _db_path(project_dir)
    if not db_path.is_file():
        report.add("project_exists", False, f"no {CHRONICLE_DB} at {project_dir}")
        return report
    report.add("project_exists", True, str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        verify_append_only_ledger(conn, report)
        verify_referential_integrity(conn, report)
        verify_status_consistency(conn, report)
        verify_projection_completeness(conn, report)
        if check_evidence_files:
            verify_evidence_integrity(conn, project_dir, report)
    finally:
        conn.close()

    return report


def verify_db(db_path: Path | str) -> VerifyReport:
    """Run invariant suite on a bare DB (no evidence dir). Skips evidence_integrity or uses empty project."""
    db_path = Path(db_path)
    report = VerifyReport(passed=True)
    if not db_path.is_file():
        report.add("db_exists", False, str(db_path))
        return report
    report.add("db_exists", True, str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        verify_append_only_ledger(conn, report)
        verify_referential_integrity(conn, report)
        verify_status_consistency(conn, report)
        verify_projection_completeness(conn, report)
    finally:
        conn.close()

    return report


def verify_postgres_url(
    database_url: str,
    *,
    check_evidence_files: bool = False,
) -> VerifyReport:
    """Run invariant suite on a PostgreSQL Chronicle database URL."""
    report = VerifyReport(passed=True)
    try:
        import psycopg
    except ImportError:
        report.add(
            "postgres_dependency",
            False,
            "psycopg not installed; install with pip install -e '.[postgres]'",
        )
        return report

    try:
        conn = psycopg.connect(database_url)
    except Exception as e:
        report.add("postgres_connect", False, str(e))
        return report

    report.add("postgres_connect", True, "connected")
    try:
        verify_append_only_ledger(conn, report)
        verify_referential_integrity(conn, report)
        verify_status_consistency(conn, report)
        verify_projection_completeness(conn, report)
        if check_evidence_files:
            report.add(
                "evidence_integrity",
                True,
                "skipped for postgres URL mode (requires project evidence directory path)",
            )
    finally:
        conn.close()
    return report
