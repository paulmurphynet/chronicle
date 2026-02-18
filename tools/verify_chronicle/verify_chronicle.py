"""
Standalone verifier for .chronicle files (ZIP export). Phase 8.
Uses only Python stdlib: zipfile, json, sqlite3, hashlib, tempfile.
No Chronicle package required — recipients can "verify it yourself".
"""

import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

# Manifest required keys (Spec evidence.md 4.1.1, export_import.py)
MANIFEST_REQUIRED_KEYS = ("format_version", "investigation_uid")
MIN_FORMAT_VERSION = 1

# Minimal DB tables that must exist
REQUIRED_TABLES = ("events", "schema_version", "investigation", "claim", "evidence_item")


def _report(name: str, passed: bool, detail: str, results: list) -> None:
    results.append((name, passed, detail))


def verify_manifest(manifest: dict, results: list) -> None:
    """Validate manifest.json: required keys and format_version."""
    for key in MANIFEST_REQUIRED_KEYS:
        if key not in manifest:
            _report("manifest", False, f"missing key: {key}", results)
            return
    try:
        v = int(manifest["format_version"])
    except (TypeError, ValueError):
        _report("manifest", False, "format_version must be an integer", results)
        return
    if v < MIN_FORMAT_VERSION:
        _report("manifest", False, f"format_version {v} < {MIN_FORMAT_VERSION}", results)
        return
    _report("manifest", True, f"format_version={v}, investigation_uid present", results)


def verify_db_schema(conn: sqlite3.Connection, results: list) -> None:
    """Check schema_version and required tables exist."""
    try:
        cur = conn.execute(
            "SELECT component, version FROM schema_version WHERE component IN ('event_store', 'read_model')"
        )
        rows = cur.fetchall()
        if not rows:
            _report("schema_version", False, "no event_store or read_model version row", results)
        else:
            _report("schema_version", True, f"versions: {dict(rows)}", results)
    except sqlite3.OperationalError as e:
        _report("schema_version", False, str(e), results)
        return

    missing = []
    for table in REQUIRED_TABLES:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cur.fetchone() is None:
            missing.append(table)
    if missing:
        _report("schema_tables", False, f"missing tables: {missing}", results)
    else:
        _report("schema_tables", True, "all required tables present", results)


def verify_evidence_hashes(zf: zipfile.ZipFile, conn: sqlite3.Connection, results: list) -> None:
    """Validate each evidence file in the ZIP matches content_hash in DB."""
    try:
        cur = conn.execute("SELECT evidence_uid, uri, content_hash FROM evidence_item")
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        _report("evidence_hashes", False, str(e), results)
        return

    if not rows:
        _report("evidence_hashes", True, "no evidence items", results)
        return

    failed = []
    for evidence_uid, uri, content_hash in rows:
        if not uri or ".." in uri or uri.startswith("/"):
            failed.append(f"{evidence_uid}: invalid uri")
            continue
        try:
            data = zf.read(uri)
        except KeyError:
            failed.append(f"{evidence_uid}: file missing in ZIP ({uri})")
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != content_hash:
            failed.append(f"{evidence_uid}: hash mismatch")

    if failed:
        _report(
            "evidence_hashes",
            False,
            "; ".join(failed[:5]) + (" ..." if len(failed) > 5 else ""),
            results,
        )
    else:
        _report("evidence_hashes", True, f"all {len(rows)} evidence file(s) match hash", results)


def verify_append_only_ledger(conn: sqlite3.Connection, results: list) -> None:
    """Events table: no recorded_at reversals (append-only)."""
    try:
        cur = conn.execute("SELECT event_id, recorded_at FROM events ORDER BY rowid ASC")
        rows = cur.fetchall()
        if not rows:
            _report("append_only_ledger", True, "no events", results)
            return
        prev = ""
        for eid, rec in rows:
            if rec < prev:
                _report(
                    "append_only_ledger", False, f"recorded_at reversal at event_id={eid}", results
                )
                return
            prev = rec
        _report("append_only_ledger", True, f"{len(rows)} events in order", results)
    except sqlite3.OperationalError as e:
        _report("append_only_ledger", False, str(e), results)


def _summary_from_chronicle(zf: zipfile.ZipFile, conn: sqlite3.Connection) -> dict:
    """Return a short 'what's inside' summary (investigation_uid, claim_count, evidence_count)."""
    out = {}
    try:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        out["investigation_uid"] = manifest.get("investigation_uid", "")
        out["title"] = manifest.get("title") or "(no title)"
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        cur = conn.execute("SELECT COUNT(*) FROM claim")
        out["claim_count"] = cur.fetchone()[0]
    except sqlite3.OperationalError:
        pass
    try:
        cur = conn.execute("SELECT COUNT(*) FROM evidence_item")
        out["evidence_count"] = cur.fetchone()[0]
    except sqlite3.OperationalError:
        pass
    return out


def verify_chronicle_file(
    path: Path, *, run_invariants: bool = True
) -> list[tuple[str, bool, str]]:
    """
    Validate a .chronicle file (ZIP). Returns list of (check_name, passed, detail).
    Checks: manifest, DB schema, evidence hashes; optionally append_only ledger.
    """
    path = Path(path)
    results: list[tuple[str, bool, str]] = []

    if not path.is_file():
        _report("file", False, f"not a file: {path}", results)
        return results
    if path.suffix != ".chronicle":
        _report("file", False, "extension must be .chronicle", results)
        return results
    _report("file", True, str(path), results)

    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as e:
        _report("zip", False, str(e), results)
        return results

    with zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            _report("zip", False, "missing manifest.json", results)
            return results
        if "chronicle.db" not in names:
            _report("zip", False, "missing chronicle.db", results)
            return results

        _report("zip", True, "valid ZIP with manifest and DB", results)

        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            _report("manifest", False, str(e), results)
            return results

        verify_manifest(manifest, results)

        with tempfile.TemporaryDirectory(prefix="chronicle_verify_") as tmp:
            db_path = Path(tmp) / "chronicle.db"
            db_path.write_bytes(zf.read("chronicle.db"))
            conn = sqlite3.connect(str(db_path))
            try:
                verify_db_schema(conn, results)
                verify_evidence_hashes(zf, conn, results)
                if run_invariants:
                    verify_append_only_ledger(conn, results)
            finally:
                conn.close()

    return results


def main() -> int:
    """CLI entry: verify_chronicle path/to/file.chronicle [--no-invariants] [--summary] [--json]."""
    args = sys.argv[1:]
    run_invariants = True
    show_summary = False
    json_output = False
    if "--no-invariants" in args:
        args.remove("--no-invariants")
        run_invariants = False
    if "--summary" in args:
        args.remove("--summary")
        show_summary = True
    if "--json" in args:
        args.remove("--json")
        json_output = True
    if "-h" in args or "--help" in args or not args:
        print(
            "Usage: chronicle-verify <path/to/file.chronicle> [--no-invariants] [--summary] [--json]\n"
            "       python -m tools.verify_chronicle <file.chronicle> [options]\n"
            "Options:\n  --no-invariants  Skip append-only ledger check\n"
            "  --summary         Print 'What's inside' (investigation, claims, evidence count) when verified\n"
            "  --json            Output machine-readable result (verified, checks, optional summary)",
            file=sys.stderr if not args else sys.stdout,
        )
        return 0 if ("-h" in args or "--help" in args) else 2
    path = Path(args[0])
    results = verify_chronicle_file(path, run_invariants=run_invariants)
    all_passed = all(r[1] for r in results)

    if json_output:
        out = {
            "verified": all_passed,
            "checks": [{"name": n, "passed": p, "detail": d} for n, p, d in results],
        }
        if all_passed and show_summary:
            try:
                with (
                    zipfile.ZipFile(path, "r") as zf,
                    tempfile.TemporaryDirectory(prefix="chronicle_verify_") as tmp,
                ):
                    db_path = Path(tmp) / "chronicle.db"
                    db_path.write_bytes(zf.read("chronicle.db"))
                    conn = sqlite3.connect(str(db_path))
                    try:
                        out["summary"] = _summary_from_chronicle(zf, conn)
                    finally:
                        conn.close()
            except Exception:
                pass
        print(json.dumps(out))
        return 0 if all_passed else 1
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    if all_passed:
        print("")
        print("Result: VERIFIED")
        if show_summary:
            try:
                with (
                    zipfile.ZipFile(path, "r") as zf,
                    tempfile.TemporaryDirectory(prefix="chronicle_verify_") as tmp,
                ):
                    db_path = Path(tmp) / "chronicle.db"
                    db_path.write_bytes(zf.read("chronicle.db"))
                    conn = sqlite3.connect(str(db_path))
                    try:
                        s = _summary_from_chronicle(zf, conn)
                        print("What's inside:")
                        if "investigation_uid" in s:
                            print(f"  Investigation: {s['investigation_uid']}")
                        if "title" in s:
                            print(f"  Title: {s['title']}")
                        if "claim_count" in s:
                            print(f"  Claims: {s['claim_count']}")
                        if "evidence_count" in s:
                            print(f"  Evidence items: {s['evidence_count']}")
                    finally:
                        conn.close()
            except Exception:
                pass
        return 0
    print("")
    print("Result: NOT VERIFIED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
