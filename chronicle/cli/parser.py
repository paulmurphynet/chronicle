"""CLI parser construction for Chronicle."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path


def build_parser(_path_arg: Callable[[str], Path]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronicle", description="Chronicle — epistemic ledger for investigations"
    )
    parser.add_argument(
        "--actor-id",
        default=os.environ.get("CHRONICLE_ACTOR_ID"),
        help="Actor ID for attribution on write commands (env: CHRONICLE_ACTOR_ID)",
    )
    parser.add_argument(
        "--actor-type",
        default=os.environ.get("CHRONICLE_ACTOR_TYPE") or "human",
        help="Actor type: human, tool, or system (env: CHRONICLE_ACTOR_TYPE)",
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

    reviewer_ledger_p = subparsers.add_parser(
        "reviewer-decision-ledger",
        help="TE-04: Export unified reviewer decision ledger (decisions + unresolved tensions)",
    )
    reviewer_ledger_p.add_argument("investigation_uid", help="Investigation UID")
    reviewer_ledger_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    reviewer_ledger_p.add_argument(
        "--limit",
        "-n",
        type=int,
        default=500,
        metavar="N",
        help="Max decision events to include (default: 500)",
    )

    review_packet_p = subparsers.add_parser(
        "review-packet",
        help="TE-05: Build one unified review packet (policy + decision ledger + reasoning + audit bundle)",
    )
    review_packet_p.add_argument("investigation_uid", help="Investigation UID")
    review_packet_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    review_packet_p.add_argument(
        "--output",
        "-o",
        default=None,
        type=_path_arg,
        help="Write JSON packet to file (default: stdout)",
    )
    review_packet_p.add_argument(
        "--limit-claims",
        type=int,
        default=200,
        metavar="N",
        help="Max claims to include in packet reasoning/audit sections (default: 200)",
    )
    review_packet_p.add_argument(
        "--decision-limit",
        type=int,
        default=500,
        metavar="N",
        help="Max decision events in reviewer ledger section (default: 500)",
    )
    review_packet_p.add_argument(
        "--no-reasoning-briefs",
        action="store_true",
        help="Exclude per-claim reasoning briefs from packet",
    )
    review_packet_p.add_argument(
        "--full-trail",
        action="store_true",
        help="Include full event history in audit bundle section",
    )
    review_packet_p.add_argument(
        "--as-of",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Defensibility snapshot/briefs as of this date",
    )
    review_packet_p.add_argument(
        "--as-of-event",
        type=str,
        default=None,
        metavar="EVENT_ID",
        help="Defensibility snapshot/briefs as of this event ID",
    )
    review_packet_p.add_argument(
        "--viewing-profile-id",
        default=None,
        help="Viewing policy profile id (default: active policy.json)",
    )
    review_packet_p.add_argument(
        "--built-under-profile-id",
        default=None,
        help="Built-under profile id override (default: latest checkpoint metadata)",
    )
    review_packet_p.add_argument(
        "--built-under-policy-version",
        default=None,
        help="Built-under policy version/hash override",
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

    replay_p = subparsers.add_parser(
        "replay",
        help="Rebuild read model from event log (optionally up to an event or time); for recovery or state-at-point",
    )
    replay_p.add_argument(
        "--path",
        "-p",
        default=".",
        type=_path_arg,
        help="Project path (default: current directory)",
    )
    replay_p.add_argument(
        "--up-to-event",
        metavar="EVENT_ID",
        help="Replay events from the start up to and including this event_id",
    )
    replay_p.add_argument(
        "--up-to-time",
        metavar="ISO8601",
        help="Replay events with recorded_at <= this time (ISO-8601)",
    )

    snapshot_p = subparsers.add_parser(
        "snapshot",
        help="Read-model snapshot at event N for scale: create or restore from snapshot + tail replay",
    )
    snapshot_sub = snapshot_p.add_subparsers(dest="snapshot_command", required=True)
    snapshot_create_p = snapshot_sub.add_parser(
        "create", help="Create snapshot of read model at event N"
    )
    snapshot_create_p.add_argument("--path", "-p", default=".", type=_path_arg, help="Project path")
    snapshot_create_p.add_argument(
        "--at-event",
        required=True,
        metavar="EVENT_ID",
        help="Snapshot as of this event_id (inclusive)",
    )
    snapshot_create_p.add_argument(
        "--output", "-o", required=True, type=_path_arg, help="Output path for snapshot SQLite file"
    )
    snapshot_restore_p = snapshot_sub.add_parser(
        "restore", help="Restore read model from snapshot, then replay tail events"
    )
    snapshot_restore_p.add_argument(
        "--path", "-p", default=".", type=_path_arg, help="Project path"
    )
    snapshot_restore_p.add_argument(
        "--snapshot", "-s", required=True, type=_path_arg, help="Path to snapshot SQLite file"
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
    neo4j_sync_p.add_argument(
        "--dedupe-evidence-by-content-hash",
        action="store_true",
        help="Full deduplication: one EvidenceItem per content_hash, one Claim per hash(claim_text); lineage via CONTAINS_EVIDENCE and CONTAINS_CLAIM. Can also set NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1",
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
    policy_compat_p = policy_sub.add_parser(
        "compat",
        help="Compare built-under policy vs viewing policy for an investigation",
    )
    policy_compat_p.add_argument("--path", "-p", default=".", type=_path_arg, help="Project path")
    policy_compat_p.add_argument(
        "--investigation",
        "-i",
        required=True,
        help="Investigation UID",
    )
    policy_compat_p.add_argument(
        "--viewing-profile-id",
        default=None,
        help="Viewing profile id (default: active policy.json)",
    )
    policy_compat_p.add_argument(
        "--built-under-profile-id",
        default=None,
        help="Built-under profile id override (default: latest checkpoint metadata)",
    )
    policy_compat_p.add_argument(
        "--built-under-policy-version",
        default=None,
        help="Built-under policy version/hash override",
    )
    policy_compat_p.add_argument(
        "--json",
        action="store_true",
        help="Output compatibility result as JSON",
    )

    return parser
