"""
Standalone verifier for .chronicle files (ZIP export). Phase 8.
Uses only Python stdlib: zipfile, json, sqlite3, hashlib, tempfile.
No Chronicle package required — recipients can "verify it yourself".
"""

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

# Manifest required keys (Spec evidence.md 4.1.1, export_import.py)
MANIFEST_REQUIRED_KEYS = ("format_version", "investigation_uid")
MIN_FORMAT_VERSION = 1

# Minimal DB tables that must exist
REQUIRED_TABLES = ("events", "schema_version", "investigation", "claim", "evidence_item")
ARCHIVE_REQUIRED_FILES = frozenset({"manifest.json", "chronicle.db"})
EVIDENCE_DIR = "evidence"


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return val if val > 0 else default


MAX_IMPORT_ARCHIVE_ENTRIES = _env_int("CHRONICLE_MAX_IMPORT_ARCHIVE_ENTRIES", 5000)
MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES",
    2 * 1024 * 1024 * 1024,
)
MAX_IMPORT_ARCHIVE_MEMBER_BYTES = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_MEMBER_BYTES",
    512 * 1024 * 1024,
)
MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO = _env_int(
    "CHRONICLE_MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO",
    200,
)


def _validate_archive_member_name(name: str) -> PurePosixPath:
    raw = (name or "").strip()
    if not raw:
        raise ValueError("empty archive member name")
    if raw.startswith("/") or raw.startswith("\\") or "\\" in raw:
        raise ValueError(f"unsafe archive member path {name!r}")
    member = PurePosixPath(raw)
    parts = member.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe archive member path {name!r}")
    if ":" in parts[0]:
        raise ValueError(f"unsafe archive member path {name!r}")
    return member


def _is_allowed_archive_member(member: PurePosixPath) -> bool:
    normalized = member.as_posix()
    if normalized in ARCHIVE_REQUIRED_FILES:
        return True
    if normalized == EVIDENCE_DIR:
        return True
    return normalized.startswith(f"{EVIDENCE_DIR}/")


def _build_archive_file_index(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = zf.infolist()
    if len(infos) > MAX_IMPORT_ARCHIVE_ENTRIES:
        raise ValueError(
            "archive has too many entries "
            f"({len(infos)} > {MAX_IMPORT_ARCHIVE_ENTRIES})"
        )
    total_uncompressed = 0
    unexpected_entries: list[str] = []
    files_by_name: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        member = _validate_archive_member_name(info.filename)
        if info.flag_bits & 0x1:
            raise ValueError(f"encrypted archive member not allowed ({member.as_posix()})")
        if info.file_size > MAX_IMPORT_ARCHIVE_MEMBER_BYTES:
            raise ValueError(
                "archive member exceeds max uncompressed size "
                f"({member.as_posix()}: {info.file_size} > {MAX_IMPORT_ARCHIVE_MEMBER_BYTES})"
            )
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES:
            raise ValueError(
                "archive exceeds max uncompressed size "
                f"({total_uncompressed} > {MAX_IMPORT_ARCHIVE_UNCOMPRESSED_BYTES})"
            )
        if info.compress_size > 0 and (
            info.file_size > info.compress_size * MAX_IMPORT_ARCHIVE_COMPRESSION_RATIO
        ):
            raise ValueError(f"suspicious compression ratio for {member.as_posix()}")
        if not _is_allowed_archive_member(member):
            unexpected_entries.append(member.as_posix())
        if not info.is_dir():
            files_by_name[member.as_posix()] = info
    if unexpected_entries:
        detail = ", ".join(unexpected_entries[:5])
        if len(unexpected_entries) > 5:
            detail = f"{detail}, ..."
        raise ValueError(f"unexpected archive entries ({detail})")
    return files_by_name


def _stream_sha256_zip_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    h = hashlib.sha256()
    read_bytes = 0
    with zf.open(info, "r") as member_file:
        while True:
            chunk = member_file.read(1024 * 1024)
            if not chunk:
                break
            read_bytes += len(chunk)
            if read_bytes > MAX_IMPORT_ARCHIVE_MEMBER_BYTES:
                raise ValueError(
                    f"archive member exceeds max uncompressed size ({info.filename})"
                )
            h.update(chunk)
    return h.hexdigest()


def _copy_zip_member_to_path(zf: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(info, "r") as src, dest.open("wb") as out:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


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


def verify_evidence_hashes(
    zf: zipfile.ZipFile,
    files_by_name: dict[str, zipfile.ZipInfo],
    conn: sqlite3.Connection,
    results: list,
) -> None:
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
        info = files_by_name.get(uri)
        if info is None:
            failed.append(f"{evidence_uid}: file missing in ZIP ({uri})")
            continue
        try:
            digest = _stream_sha256_zip_member(zf, info)
        except ValueError as exc:
            failed.append(f"{evidence_uid}: {exc}")
            continue
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
        try:
            files_by_name = _build_archive_file_index(zf)
        except ValueError as exc:
            _report("zip", False, str(exc), results)
            return results
        if "manifest.json" not in files_by_name:
            _report("zip", False, "missing manifest.json", results)
            return results
        if "chronicle.db" not in files_by_name:
            _report("zip", False, "missing chronicle.db", results)
            return results

        _report("zip", True, "valid ZIP with manifest and DB", results)

        try:
            manifest = json.loads(zf.read(files_by_name["manifest.json"].filename).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            _report("manifest", False, str(e), results)
            return results

        verify_manifest(manifest, results)

        with tempfile.TemporaryDirectory(prefix="chronicle_verify_") as tmp:
            db_path = Path(tmp) / "chronicle.db"
            _copy_zip_member_to_path(zf, files_by_name["chronicle.db"], db_path)
            conn = sqlite3.connect(str(db_path))
            try:
                verify_db_schema(conn, results)
                verify_evidence_hashes(zf, files_by_name, conn, results)
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
