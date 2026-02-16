"""CLI entry point: chronicle init, chronicle create-investigation, chronicle ingest-evidence."""

import argparse
import json
import mimetypes
import sqlite3
import sys
import tempfile
from pathlib import Path

from chronicle.core.errors import ChronicleUserError
from chronicle.store import export_import as export_import_mod
from chronicle.store.project import CHRONICLE_DB, create_project, project_exists
from chronicle.store.session import ChronicleSession

# User-facing errors: show message and exit 1. All other exceptions propagate (e.g. for pytest).
_USER_ERRORS = (ValueError, FileNotFoundError, OSError, sqlite3.Error, ChronicleUserError)


def _path_arg(s: str) -> Path:
    return Path(s).resolve()


def cmd_init(path: Path) -> int:
    """Initialize a directory as a Chronicle project (creates chronicle.db and schema)."""
    if (path / CHRONICLE_DB).exists():
        print(f"Already a Chronicle project: {path}", file=sys.stderr)
        return 0
    create_project(path)
    print(f"Initialized Chronicle project at {path}")
    return 0


def cmd_create_investigation(title: str, path: Path, description: str | None) -> int:
    """Create a new investigation in the project. Spec 1.5.1."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        _event_id, investigation_uid = session.create_investigation(
            title, description=description or None
        )
        print(f"Created investigation {investigation_uid}")
        return 0


def cmd_ingest_evidence(
    file_path: Path, investigation_uid: str, path: Path, media_type: str | None
) -> int:
    """Ingest a file as evidence into an investigation. Spec 1.5.1; media type guessed if omitted."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    if not file_path.is_file():
        print(f"Not a file: {file_path}", file=sys.stderr)
        return 1
    mt = media_type
    if not mt:
        mt, _ = mimetypes.guess_type(str(file_path))
    if not mt:
        print("Could not guess media type. Use --media-type.", file=sys.stderr)
        return 1
    blob = file_path.read_bytes()
    original_filename = file_path.name
    with ChronicleSession(path) as session:
        _event_id, evidence_uid = session.ingest_evidence(
            investigation_uid,
            blob,
            mt,
            original_filename=original_filename,
        )
        print(f"Ingested {original_filename} as {evidence_uid}")
        return 0


def cmd_set_tier(investigation_uid: str, tier: str, path: Path, reason: str | None) -> int:
    """Set investigation tier (spark -> forge -> vault). Phase 1."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        event_id = session.set_tier(investigation_uid, tier, reason=reason)
        inv = session.read_model.get_investigation(investigation_uid)
        tier_display = inv.current_tier if inv else tier.strip().lower()
        print(f"Tier set to {tier_display} (event_id={event_id})")
        return 0


def cmd_export(investigation_uid: str, output: Path, path: Path) -> int:
    """Export investigation to .chronicle file."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        out = session.export_investigation(investigation_uid, output)
        print(f"Exported to {out}")
        return 0


def cmd_export_minimal(investigation_uid: str, claim_uid: str, output: Path, path: Path) -> int:
    """Export minimal .chronicle for one claim (verifier can validate it). P2.2.2."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        out = session.export_minimal_for_claim(investigation_uid, claim_uid, output)
        print(f"Exported minimal .chronicle to {out}")
        return 0


def cmd_import(chronicle_file: Path, path: Path) -> int:
    """Import .chronicle file into project (extract to empty dir or merge into existing)."""
    if not chronicle_file.is_file():
        print(f"Not a file: {chronicle_file}", file=sys.stderr)
        return 1
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    export_import_mod.import_investigation(chronicle_file, path)
    print(f"Imported {chronicle_file}")
    return 0


def cmd_policy_list(path: Path) -> int:
    """List policy profiles in the project. Phase 10."""
    if not project_exists(path):
        print(f"Not a Chronicle project. Run: chronicle init {path}", file=sys.stderr)
        return 1
    from chronicle.core.policy import list_policy_profiles

    profiles = list_policy_profiles(path)
    for p in profiles:
        active = " (active)" if p.get("is_active") else ""
        print(f"  {p['profile_id']}: {p.get('relative_path', p['path'])}{active}")
    return 0


def cmd_policy_export(path: Path, profile_id: str | None, output: Path | None) -> int:
    """Export policy to policy_profiles/ or --output file. Phase 10."""
    if not project_exists(path):
        print(f"Not a Chronicle project. Run: chronicle init {path}", file=sys.stderr)
        return 1
    from chronicle.core.policy import (
        POLICY_FILENAME,
        POLICY_PROFILES_DIR,
        export_policy_profile,
        load_policy_profile,
        load_policy_profile_by_id,
    )

    if profile_id:
        profile = load_policy_profile_by_id(path, profile_id)
        if profile is None:
            print(f"Profile not found: {profile_id}", file=sys.stderr)
            return 1
    else:
        profile = load_policy_profile(path / POLICY_FILENAME)
    if output is not None:
        out_path = output
    else:
        (path / POLICY_PROFILES_DIR).mkdir(parents=True, exist_ok=True)
        out_path = path / POLICY_PROFILES_DIR / f"{profile.profile_id}.json"
    export_policy_profile(profile, out_path)
    print(f"Exported to {out_path}")
    return 0


def cmd_policy_import(path: Path, file_path: Path, activate: bool) -> int:
    """Import policy from JSON file; optionally set as active. Phase 10."""
    if not project_exists(path):
        print(f"Not a Chronicle project. Run: chronicle init {path}", file=sys.stderr)
        return 1
    if not file_path.is_file():
        print(f"Not a file: {file_path}", file=sys.stderr)
        return 1
    from chronicle.core.policy import import_policy_to_project, load_policy_from_file

    try:
        profile = load_policy_from_file(file_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"Invalid policy: {e}", file=sys.stderr)
        return 1
    dest = import_policy_to_project(path, profile, activate=activate, overwrite=True)
    print(f"Imported {profile.profile_id} to {dest}" + (" (set as active)" if activate else ""))
    return 0


def cmd_verify_chronicle(chronicle_file: Path, no_invariants: bool) -> int:
    """Verify a .chronicle file (ZIP) without Chronicle runtime. Phase 8."""
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    path = Path(chronicle_file).resolve()
    results = verify_chronicle_file(path, run_invariants=not no_invariants)
    all_passed = all(r[1] for r in results)
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    if all_passed:
        print("Verification passed.")
        return 0
    print("One or more checks failed.", file=sys.stderr)
    return 1


def cmd_verify(path: Path, skip_evidence: bool) -> int:
    """Run invariant suite (Spec 12.7.5) and print pass/fail report."""
    from chronicle.verify import verify_project

    report = verify_project(path, check_evidence_files=not skip_evidence)
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}" + (f" — {r.detail}" if r.detail else ""))
    if report.passed:
        print("All checks passed.")
        return 0
    print("One or more checks failed.", file=sys.stderr)
    return 1


def cmd_get_defensibility(claim_uid: str, path: Path) -> int:
    """Print defensibility scorecard for a claim as JSON."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        scorecard = session.get_defensibility_score(claim_uid)
        if scorecard is None:
            print(f"Claim not found: {claim_uid}", file=sys.stderr)
            return 1
        out = {
            "claim_uid": scorecard.claim_uid,
            "provenance_quality": scorecard.provenance_quality,
            "corroboration": scorecard.corroboration,
            "contradiction_status": scorecard.contradiction_status,
            "temporal_validity": scorecard.temporal_validity,
            "attribution_posture": scorecard.attribution_posture,
            "decomposition_precision": scorecard.decomposition_precision,
        }
        print(json.dumps(out, indent=2))
        return 0


def cmd_neo4j_export(path: Path, output: Path) -> int:
    """Export read model to CSV for Neo4j rebuild (Spec 14.6.4, 16.8)."""
    from chronicle.store.neo4j_export import export_project_to_neo4j_csv

    out = export_project_to_neo4j_csv(path, output)
    print(f"Exported to {out} (use neo4j/rebuild/*.cyp with Neo4j import dir)")
    return 0


def cmd_neo4j_sync(path: Path) -> int:
    """Sync read model to Neo4j (optional; requires [neo4j] and NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)."""
    import os

    try:
        from chronicle.store.neo4j_sync import sync_project_to_neo4j
    except ImportError:
        print(
            "Neo4j driver not installed. Install with: pip install chronicle-standard[neo4j]",
            file=sys.stderr,
        )
        return 1

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")

    if not uri or not uri.strip():
        print(
            "NEO4J_URI is not set. Set NEO4J_URI (and optionally NEO4J_USER, NEO4J_PASSWORD) to sync to Neo4j.",
            file=sys.stderr,
        )
        return 1
    if not password:
        print("NEO4J_PASSWORD is not set.", file=sys.stderr)
        return 1

    try:
        sync_project_to_neo4j(path, uri.strip(), user or "neo4j", password)
        print("Synced read model to Neo4j.")
        return 0
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(str(e), file=sys.stderr)
        return 1


def cmd_audit_trail(investigation_uid: str, path: Path, limit: int = 500) -> int:
    """E6: Print audit trail of human decisions (tier changes, dismissals) for an investigation."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            print(f"Investigation not found: {investigation_uid}", file=sys.stderr)
            return 1
        trail = session.get_human_decisions_audit_trail(investigation_uid, limit=limit)
        print(json.dumps(trail, indent=2))
    return 0


def cmd_audit_export(
    investigation_uid: str,
    path: Path,
    output: Path | None = None,
    include_full_trail: bool = False,
    limit_claims: int = 500,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
) -> int:
    """B.1: Export audit pack for an investigation (evidence, claims, links, defensibility snapshot, human decisions). One-shot for compliance."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    try:
        with ChronicleSession(path) as session:
            bundle = session.get_audit_export_bundle(
                investigation_uid,
                include_full_trail=include_full_trail,
                limit_claims=limit_claims,
                as_of_date=as_of_date,
                as_of_event_id=as_of_event_id,
            )
        out_json = json.dumps(bundle, indent=2)
        if output is not None:
            output.write_text(out_json, encoding="utf-8")
            print(f"Audit pack written to {output}", file=sys.stderr)
        else:
            print(out_json)
    except ValueError as e:
        if "not found" in str(e).lower():
            print(f"Investigation not found: {investigation_uid}", file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
        return 1
    return 0


def cmd_reasoning_trail(
    path: Path,
    claim_uid: str | None = None,
    checkpoint_uid: str | None = None,
    format: str = "json",
    limit: int = 500,
) -> int:
    """Export reasoning trail for a claim or checkpoint. Phase 6."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    if (claim_uid is None) == (checkpoint_uid is None):
        print("Exactly one of --claim or --checkpoint is required.", file=sys.stderr)
        return 1
    with ChronicleSession(path) as session:
        if claim_uid is not None:
            trail = session.get_reasoning_trail_claim(claim_uid, limit=limit)
            if trail is None:
                print(f"Claim not found: {claim_uid}", file=sys.stderr)
                return 1
            if format == "html":
                from chronicle.store.commands.reasoning_trail import reasoning_trail_claim_to_html

                print(reasoning_trail_claim_to_html(trail))
            else:
                print(json.dumps(trail, indent=2))
        else:
            assert checkpoint_uid is not None  # exactly one of --claim or --checkpoint
            trail = session.get_reasoning_trail_checkpoint(checkpoint_uid)
            if trail is None:
                print(f"Checkpoint not found: {checkpoint_uid}", file=sys.stderr)
                return 1
            if format == "html":
                from chronicle.store.commands.reasoning_trail import (
                    reasoning_trail_checkpoint_to_html,
                )

                print(reasoning_trail_checkpoint_to_html(trail))
            else:
                print(json.dumps(trail, indent=2))
    return 0


def cmd_reasoning_brief(
    path: Path,
    claim_uid: str,
    format: str = "html",
    limit: int = 500,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
) -> int:
    """Export reasoning brief for a claim. B.2: Optional --as-of or --as-of-event for defensibility at a point in time."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    try:
        with ChronicleSession(path) as session:
            brief = session.get_reasoning_brief(
                claim_uid,
                limit=limit,
                as_of_date=as_of_date,
                as_of_event_id=as_of_event_id,
            )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    if brief is None:
        print(f"Claim not found: {claim_uid}", file=sys.stderr)
        return 1
    if format == "html":
        from chronicle.store.commands.reasoning_brief import reasoning_brief_to_html

        print(reasoning_brief_to_html(brief))
    else:
        print(json.dumps(brief, indent=2))
    return 0


def cmd_quickstart_rag(path: Path | None, text_file: Path | None) -> int:
    """Run a minimal RAG-style flow: create project, investigation, ingest, claim, link; print defensibility. Phase 1 RAG friction."""
    if path is None:
        tmp = tempfile.mkdtemp(prefix="chronicle_rag_")
        path = Path(tmp)
        print(f"Project at: {path}")
    path = path.resolve()
    create_project(path)
    if text_file is not None and text_file.is_file():
        sample_text = text_file.read_text(encoding="utf-8", errors="replace").strip()
    else:
        sample_text = "The company reported revenue of $1.2M in Q1 2024."
    if not sample_text:
        sample_text = "The company reported revenue of $1.2M in Q1 2024."
    blob = sample_text.encode("utf-8")

    with ChronicleSession(path) as session:
        session.create_investigation("RAG quickstart")
        inv_uid = session.read_model.list_investigations()[0].investigation_uid
        _, ev_uid = session.ingest_evidence(inv_uid, blob, "text/plain")
        claim_text = (
            "Revenue in Q1 2024 was $1.2M."
            if "1.2" in sample_text and "revenue" in sample_text.lower()
            else (sample_text[:200] + "..." if len(sample_text) > 200 else sample_text)
        )
        _, claim_uid = session.propose_claim(inv_uid, claim_text)
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(blob.decode("utf-8"))},
            quote=sample_text[:500] if len(sample_text) > 500 else sample_text,
        )
        session.link_support(inv_uid, span_uid, claim_uid)
        scorecard = session.get_defensibility_score(claim_uid)
        print(f"Investigation: {inv_uid}")
        print(f"Claim:        {claim_uid}")
        if scorecard:
            print(f"Defensibility: {scorecard.provenance_quality}")
            print(f"  Corroboration: {scorecard.corroboration}")
            print(f"  Contradiction:  {scorecard.contradiction_status}")
        else:
            print("Defensibility: (no scorecard)")
        print("")
        print(
            f"View reasoning brief: chronicle reasoning-brief {claim_uid} --path {path} --format html > brief.html"
        )
    return 0


def cmd_similar_claims(path: Path, claim_uid: str, limit: int = 10) -> int:
    """List claims similar to the given claim (semantic). Requires CHRONICLE_EMBEDDING_ENABLED."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        pairs = session.get_similar_claims(claim_uid, limit=limit)
        if not pairs:
            print(
                "No similar claims (enable embeddings with CHRONICLE_EMBEDDING_ENABLED)",
                file=sys.stderr,
            )
            return 0
        for uid, score in pairs:
            print(f"{uid}\t{score:.4f}")
    return 0


def main() -> int:
    """Parse CLI args and dispatch to command handlers."""
    parser = argparse.ArgumentParser(
        prog="chronicle", description="Chronicle — epistemic ledger for investigations"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init", help="Initialize a Chronicle project directory")
    init_p.add_argument(
        "path",
        nargs="?",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    quickstart_rag_p = subparsers.add_parser(
        "quickstart-rag",
        help="Run a minimal RAG flow: project, investigation, ingest, claim, link; print defensibility (RAG in 5 min)",
    )
    quickstart_rag_p.add_argument(
        "--path",
        "-p",
        default=None,
        type=_path_arg,
        help="Project path (default: temporary directory)",
    )
    quickstart_rag_p.add_argument(
        "--text",
        "-t",
        dest="text_file",
        default=None,
        type=Path,
        help="Text file to ingest as evidence (default: built-in sample)",
    )

    create_p = subparsers.add_parser("create-investigation", help="Create a new investigation")
    create_p.add_argument("title", help="Investigation title")
    create_p.add_argument("--description", "-d", default=None, help="Optional description")
    create_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    ingest_p = subparsers.add_parser(
        "ingest-evidence", help="Ingest a file as evidence into an investigation"
    )
    ingest_p.add_argument("file", type=Path, help="Path to the file to ingest")
    ingest_p.add_argument("--investigation", "-i", required=True, help="Investigation UID")
    ingest_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    ingest_p.add_argument(
        "--media-type", "-m", default=None, help="MIME type (default: guess from file extension)"
    )

    set_tier_p = subparsers.add_parser(
        "set-tier", help="Set investigation tier: spark -> forge -> vault (Phase 1)"
    )
    set_tier_p.add_argument("investigation_uid", help="Investigation UID")
    set_tier_p.add_argument("tier", help="Tier: spark, forge, or vault")
    set_tier_p.add_argument(
        "--reason", "-r", default=None, help="Optional reason for the transition"
    )
    set_tier_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    export_p = subparsers.add_parser("export", help="Export investigation to .chronicle file")
    export_p.add_argument("--investigation", "-i", required=True, help="Investigation UID")
    export_p.add_argument(
        "--output", "-o", required=True, type=_path_arg, help="Output .chronicle file path"
    )
    export_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    export_minimal_p = subparsers.add_parser(
        "export-minimal",
        help="Export minimal .chronicle for one claim (claim + evidence + links + tensions) for verifier (P2.2.2)",
    )
    export_minimal_p.add_argument("--investigation", "-i", required=True, help="Investigation UID")
    export_minimal_p.add_argument("--claim", "-c", required=True, help="Claim UID")
    export_minimal_p.add_argument(
        "--output", "-o", required=True, type=_path_arg, help="Output .chronicle file path"
    )
    export_minimal_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    import_p = subparsers.add_parser("import", help="Import .chronicle file into project")
    import_p.add_argument("file", type=_path_arg, help="Path to .chronicle file")
    import_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    defensibility_p = subparsers.add_parser(
        "get-defensibility",
        help="Get defensibility scorecard for a claim (Spec epistemic-tools 7.3)",
    )
    defensibility_p.add_argument("claim_uid", help="Claim UID")
    defensibility_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    reasoning_trail_p = subparsers.add_parser(
        "reasoning-trail",
        help="Export reasoning trail for a claim or checkpoint (Phase 6)",
    )
    reasoning_trail_p.add_argument("--claim", "-c", default=None, help="Claim UID")
    reasoning_trail_p.add_argument("--checkpoint", "-k", default=None, help="Checkpoint UID")
    reasoning_trail_p.add_argument(
        "--format",
        "-f",
        choices=("json", "html"),
        default="json",
        help="Output format (default: json)",
    )
    reasoning_trail_p.add_argument(
        "--limit",
        "-n",
        type=int,
        default=500,
        metavar="N",
        help="Max events for claim trail (default: 500)",
    )
    reasoning_trail_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    reasoning_brief_p = subparsers.add_parser(
        "reasoning-brief",
        help="Export reasoning brief for a claim (claim + defensibility + evidence + tensions + trail)",
    )
    reasoning_brief_p.add_argument("claim_uid", help="Claim UID")
    reasoning_brief_p.add_argument(
        "--format",
        "-f",
        choices=("json", "html"),
        default="html",
        help="Output format (default: html)",
    )
    reasoning_brief_p.add_argument(
        "--limit",
        "-n",
        type=int,
        default=500,
        metavar="N",
        help="Max events in trail (default: 500)",
    )
    reasoning_brief_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    reasoning_brief_p.add_argument(
        "--as-of",
        type=str,
        default=None,
        metavar="ISO8601",
        help="B.2: Defensibility as of this date",
    )
    reasoning_brief_p.add_argument(
        "--as-of-event",
        type=str,
        default=None,
        metavar="EVENT_ID",
        help="B.2: Defensibility as of this event ID",
    )

    similar_p = subparsers.add_parser(
        "similar-claims",
        help="List claims similar to the given claim (semantic; requires CHRONICLE_EMBEDDING_ENABLED)",
    )
    similar_p.add_argument("claim_uid", help="Claim UID")
    similar_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    similar_p.add_argument(
        "--limit",
        "-n",
        type=int,
        default=10,
        metavar="N",
        help="Max similar claims (default: 10)",
    )

    audit_trail_p = subparsers.add_parser(
        "audit-trail",
        help="E6: Export audit trail of human decisions (tier changes, dismissals) for an investigation",
    )
    audit_trail_p.add_argument("investigation_uid", help="Investigation UID")
    audit_trail_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    audit_trail_p.add_argument(
        "--limit",
        "-n",
        type=int,
        default=500,
        metavar="N",
        help="Max events to return (default: 500)",
    )

    audit_export_p = subparsers.add_parser(
        "audit-export",
        help="B.1: Export audit pack for an investigation (evidence, claims, links, defensibility, human decisions). One-shot for compliance.",
    )
    audit_export_p.add_argument("investigation_uid", help="Investigation UID")
    audit_export_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    audit_export_p.add_argument(
        "--output",
        "-o",
        type=_path_arg,
        default=None,
        metavar="FILE",
        help="Write JSON to file (default: stdout)",
    )
    audit_export_p.add_argument(
        "--full-trail",
        action="store_true",
        help="Include full event history",
    )
    audit_export_p.add_argument(
        "--limit-claims",
        type=int,
        default=500,
        metavar="N",
        help="Max claims to include (default: 500)",
    )
    audit_export_p.add_argument(
        "--as-of",
        type=str,
        default=None,
        metavar="ISO8601",
        help="B.2: Defensibility snapshot as of this date",
    )
    audit_export_p.add_argument(
        "--as-of-event",
        type=str,
        default=None,
        metavar="EVENT_ID",
        help="B.2: Defensibility snapshot as of this event ID",
    )

    verify_p = subparsers.add_parser("verify", help="Run invariant suite on project (Spec 12.7.5)")
    verify_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    verify_p.add_argument(
        "--skip-evidence", action="store_true", help="Skip evidence file hash checks"
    )

    verify_chronicle_p = subparsers.add_parser(
        "verify-chronicle",
        help="Verify a .chronicle file (ZIP) without Chronicle runtime (Phase 8)",
    )
    verify_chronicle_p.add_argument(
        "file",
        type=_path_arg,
        help="Path to .chronicle file",
    )
    verify_chronicle_p.add_argument(
        "--no-invariants",
        action="store_true",
        help="Skip append-only ledger check",
    )

    neo4j_p = subparsers.add_parser(
        "neo4j-export", help="Export read model to CSV for Neo4j rebuild (Phase 14)"
    )
    neo4j_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    neo4j_p.add_argument(
        "--output", "-o", required=True, type=_path_arg, help="Output directory for CSV files"
    )

    neo4j_sync_p = subparsers.add_parser(
        "neo4j-sync",
        help="Sync read model to Neo4j (requires [neo4j] extra and NEO4J_URI, NEO4J_PASSWORD)",
    )
    neo4j_sync_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )

    policy_p = subparsers.add_parser(
        "policy", help="List, export, or import policy profiles (Phase 10)"
    )
    policy_sub = policy_p.add_subparsers(dest="policy_command", required=True)
    policy_list_p = policy_sub.add_parser("list", help="List available policy profiles")
    policy_list_p.add_argument("--path", "-p", default=".", type=_path_arg, help="Project path")
    policy_export_p = policy_sub.add_parser(
        "export", help="Export policy to policy_profiles/ or --output"
    )
    policy_export_p.add_argument("--path", "-p", default=".", type=_path_arg, help="Project path")
    policy_export_p.add_argument(
        "--profile-id", default=None, help="Export this profile id (default: active)"
    )
    policy_export_p.add_argument(
        "--output", "-o", default=None, type=_path_arg, help="Output file path"
    )
    policy_import_p = policy_sub.add_parser("import", help="Import policy from JSON file")
    policy_import_p.add_argument("file", type=_path_arg, help="Path to .json policy file")
    policy_import_p.add_argument("--path", "-p", default=".", type=_path_arg, help="Project path")
    policy_import_p.add_argument(
        "--activate", action="store_true", help="Set as active policy (policy.json)"
    )

    args = parser.parse_args()
    try:
        if args.command == "init":
            return cmd_init(args.path)
        if args.command == "quickstart-rag":
            return cmd_quickstart_rag(args.path, args.text_file)
        if args.command == "create-investigation":
            return cmd_create_investigation(args.title, args.path, args.description)
        if args.command == "ingest-evidence":
            return cmd_ingest_evidence(args.file, args.investigation, args.path, args.media_type)
        if args.command == "set-tier":
            return cmd_set_tier(args.investigation_uid, args.tier, args.path, args.reason)
        if args.command == "export":
            return cmd_export(args.investigation, args.output, args.path)
        if args.command == "export-minimal":
            return cmd_export_minimal(args.investigation, args.claim, args.output, args.path)
        if args.command == "import":
            return cmd_import(args.file, args.path)
        if args.command == "get-defensibility":
            return cmd_get_defensibility(args.claim_uid, args.path)
        if args.command == "reasoning-trail":
            return cmd_reasoning_trail(
                args.path,
                claim_uid=args.claim,
                checkpoint_uid=args.checkpoint,
                format=args.format,
                limit=args.limit,
            )
        if args.command == "reasoning-brief":
            return cmd_reasoning_brief(
                args.path,
                claim_uid=args.claim_uid,
                format=args.format,
                limit=args.limit,
                as_of_date=getattr(args, "as_of", None),
                as_of_event_id=getattr(args, "as_of_event", None),
            )
        if args.command == "similar-claims":
            return cmd_similar_claims(args.path, args.claim_uid, limit=args.limit)
        if args.command == "audit-trail":
            return cmd_audit_trail(args.investigation_uid, args.path, args.limit)
        if args.command == "audit-export":
            return cmd_audit_export(
                args.investigation_uid,
                args.path,
                output=args.output,
                include_full_trail=getattr(args, "full_trail", False),
                limit_claims=getattr(args, "limit_claims", 500),
                as_of_date=getattr(args, "as_of", None),
                as_of_event_id=getattr(args, "as_of_event", None),
            )
        if args.command == "verify":
            return cmd_verify(args.path, args.skip_evidence)
        if args.command == "verify-chronicle":
            return cmd_verify_chronicle(args.file, args.no_invariants)
        if args.command == "neo4j-export":
            return cmd_neo4j_export(args.path, args.output)
        if args.command == "neo4j-sync":
            return cmd_neo4j_sync(args.path)
        if args.command == "policy":
            if args.policy_command == "list":
                return cmd_policy_list(args.path)
            if args.policy_command == "export":
                return cmd_policy_export(args.path, args.profile_id, args.output)
            if args.policy_command == "import":
                return cmd_policy_import(args.path, args.file, args.activate)
        return 0
    except _USER_ERRORS as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
