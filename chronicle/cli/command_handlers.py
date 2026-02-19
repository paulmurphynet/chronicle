"""CLI command handlers for Chronicle."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from chronicle.cli import project_commands
from chronicle.core.errors import ChronicleUserError
from chronicle.store.project import (
    CHRONICLE_DB,
    create_project,
    project_exists,
)
from chronicle.store.session import ChronicleSession


def cmd_init(path: Path) -> int:
    """Initialize a directory as a Chronicle project (creates chronicle.db and schema)."""
    return project_commands.cmd_init(path)


def cmd_create_investigation(
    title: str,
    path: Path,
    description: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Create a new investigation in the project. Spec 1.5.1."""
    return project_commands.cmd_create_investigation(
        title,
        path,
        description,
        actor_id=actor_id,
        actor_type=actor_type,
    )


def cmd_ingest_evidence(
    file_path: Path,
    investigation_uid: str,
    path: Path,
    media_type: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Ingest a file as evidence into an investigation. Spec 1.5.1; media type guessed if omitted."""
    return project_commands.cmd_ingest_evidence(
        file_path,
        investigation_uid,
        path,
        media_type,
        actor_id=actor_id,
        actor_type=actor_type,
    )


def cmd_set_tier(
    investigation_uid: str,
    tier: str,
    path: Path,
    reason: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Set investigation tier (spark -> forge -> vault). Phase 1."""
    return project_commands.cmd_set_tier(
        investigation_uid,
        tier,
        path,
        reason,
        actor_id=actor_id,
        actor_type=actor_type,
    )


def cmd_export(investigation_uid: str, output: Path, path: Path) -> int:
    """Export investigation to .chronicle file."""
    return project_commands.cmd_export(investigation_uid, output, path)


def cmd_export_minimal(investigation_uid: str, claim_uid: str, output: Path, path: Path) -> int:
    """Export minimal .chronicle for one claim (verifier can validate it). P2.2.2."""
    return project_commands.cmd_export_minimal(investigation_uid, claim_uid, output, path)


def cmd_import(chronicle_file: Path, path: Path) -> int:
    """Import .chronicle file into project (extract to empty dir or merge into existing)."""
    return project_commands.cmd_import(chronicle_file, path)


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


def cmd_policy_compat(
    path: Path,
    investigation_uid: str,
    *,
    viewing_profile_id: str | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
    as_json: bool = False,
) -> int:
    """Compare built-under vs viewing policy for an investigation."""
    if not project_exists(path):
        print(f"Not a Chronicle project. Run: chronicle init {path}", file=sys.stderr)
        return 1
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            print(f"Investigation not found: {investigation_uid}", file=sys.stderr)
            return 1
        result = session.get_policy_compatibility_preflight(
            investigation_uid,
            viewing_profile_id=viewing_profile_id,
            built_under_profile_id=built_under_profile_id,
            built_under_policy_version=built_under_policy_version,
        )

    if as_json:
        print(json.dumps(result, indent=2))
        return 0

    print("Policy compatibility preflight")
    print(f"  Investigation: {result.get('investigation_uid')}")
    print(f"  Built-under: {result.get('built_under') or '(none)'}")
    print(f"  Viewing-under: {result.get('viewing_under') or '(none)'}")
    message = result.get("message")
    if message:
        print(f"  Message: {message}")
    deltas = result.get("deltas") or []
    if not deltas:
        print("  Deltas: none")
        return 0
    print("  Deltas:")
    for d in deltas:
        note = d.get("note")
        line = (
            f"    - {d.get('rule')}: built_under={d.get('built_under_value')!r}, "
            f"viewing_under={d.get('viewing_under_value')!r}"
        )
        if note:
            line += f" ({note})"
        print(line)
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


def cmd_replay(
    path: Path,
    up_to_event: str | None,
    up_to_time: str | None,
) -> int:
    """Rebuild read model from event log (optionally up to an event or time). Use for recovery or state-at-point verification."""
    if not project_exists(path):
        print(f"Not a Chronicle project: {path}", file=sys.stderr)
        return 1
    if up_to_event is not None and up_to_time is not None:
        print("Use only one of --up-to-event or --up-to-time.", file=sys.stderr)
        return 1
    from chronicle.store.schema import init_event_store_schema
    from chronicle.store.sqlite_event_store import replay_read_model

    db_path = path / CHRONICLE_DB
    conn = sqlite3.connect(str(db_path))
    try:
        init_event_store_schema(conn)
        applied = replay_read_model(
            conn,
            up_to_event_id=up_to_event,
            up_to_recorded_at=up_to_time,
        )
    finally:
        conn.close()
    if up_to_event:
        print(f"Replayed {applied} events (up to and including event_id={up_to_event!r}).")
    elif up_to_time:
        print(f"Replayed {applied} events (up to recorded_at<={up_to_time!r}).")
    else:
        print(f"Replayed {applied} events (full rebuild).")
    return 0


def cmd_snapshot_create(path: Path, at_event: str, output: Path) -> int:
    """Create read-model snapshot at event N (for scale: restore + tail replay later)."""
    if not project_exists(path):
        print(f"Not a Chronicle project: {path}", file=sys.stderr)
        return 1
    try:
        from chronicle.store.read_model_snapshot import create_read_model_snapshot

        applied = create_read_model_snapshot(path, at_event, output)
        print(f"Created snapshot at {output} (replayed {applied} events up to {at_event!r}).")
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_snapshot_restore(path: Path, snapshot: Path) -> int:
    """Restore read model from snapshot file, then replay tail events."""
    if not project_exists(path):
        print(f"Not a Chronicle project: {path}", file=sys.stderr)
        return 1
    try:
        from chronicle.store.read_model_snapshot import restore_from_snapshot

        tail_count = restore_from_snapshot(path, snapshot)
        print(f"Restored from {snapshot} and replayed {tail_count} tail events.")
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
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


def cmd_neo4j_sync(path: Path, *, dedupe_evidence_by_content_hash: bool = False) -> int:
    """Sync read model to Neo4j (optional; requires [neo4j] and NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)."""

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
        sync_project_to_neo4j(
            path,
            uri.strip(),
            user or "neo4j",
            password,
            dedupe_evidence_by_content_hash=dedupe_evidence_by_content_hash,
        )
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


def cmd_reviewer_decision_ledger(investigation_uid: str, path: Path, limit: int = 500) -> int:
    """TE-04: Print unified reviewer decision ledger for an investigation."""
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
        ledger = session.get_reviewer_decision_ledger(investigation_uid, limit=limit)
        print(json.dumps(ledger, indent=2))
    return 0


def cmd_review_packet(
    investigation_uid: str,
    path: Path,
    *,
    output: Path | None = None,
    limit_claims: int = 200,
    decision_limit: int = 500,
    include_reasoning_briefs: bool = True,
    include_full_trail: bool = False,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
    viewing_profile_id: str | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
) -> int:
    """TE-05: Build one review packet artifact for an investigation."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    try:
        with ChronicleSession(path) as session:
            packet = session.get_review_packet(
                investigation_uid,
                limit_claims=limit_claims,
                decision_limit=decision_limit,
                include_reasoning_briefs=include_reasoning_briefs,
                include_full_trail=include_full_trail,
                as_of_date=as_of_date,
                as_of_event_id=as_of_event_id,
                viewing_profile_id=viewing_profile_id,
                built_under_profile_id=built_under_profile_id,
                built_under_policy_version=built_under_policy_version,
            )
        out_json = json.dumps(packet, indent=2)
        if output is not None:
            output.write_text(out_json, encoding="utf-8")
            print(f"Review packet written to {output}", file=sys.stderr)
        else:
            print(out_json)
        return 0
    except (ChronicleUserError, ValueError) as e:
        if "not found" in str(e).lower():
            print(f"Investigation not found: {investigation_uid}", file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
        return 1


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


def cmd_quickstart_rag(
    path: Path | None,
    text_file: Path | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
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
        session.create_investigation(
            "RAG quickstart",
            actor_id=actor_id,
            actor_type=actor_type,
        )
        inv_uid = session.read_model.list_investigations()[0].investigation_uid
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            blob,
            "text/plain",
            actor_id=actor_id,
            actor_type=actor_type,
        )
        claim_text = (
            "Revenue in Q1 2024 was $1.2M."
            if "1.2" in sample_text and "revenue" in sample_text.lower()
            else (sample_text[:200] + "..." if len(sample_text) > 200 else sample_text)
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            claim_text,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(blob.decode("utf-8"))},
            quote=sample_text[:500] if len(sample_text) > 500 else sample_text,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id=actor_id,
            actor_type=actor_type,
        )
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
