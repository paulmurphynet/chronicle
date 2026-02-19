"""CLI command dispatch for Chronicle."""

from __future__ import annotations

import argparse

from chronicle.cli.command_handlers import (
    cmd_audit_export,
    cmd_audit_trail,
    cmd_create_investigation,
    cmd_export,
    cmd_export_minimal,
    cmd_get_defensibility,
    cmd_import,
    cmd_ingest_evidence,
    cmd_init,
    cmd_neo4j_export,
    cmd_neo4j_sync,
    cmd_policy_compat,
    cmd_policy_export,
    cmd_policy_import,
    cmd_policy_list,
    cmd_quickstart_rag,
    cmd_reasoning_brief,
    cmd_reasoning_trail,
    cmd_replay,
    cmd_set_tier,
    cmd_similar_claims,
    cmd_snapshot_create,
    cmd_snapshot_restore,
    cmd_verify,
    cmd_verify_chronicle,
)


def dispatch_command(args: argparse.Namespace, actor_id: str, actor_type: str) -> int:
    """Dispatch parsed args to a concrete CLI command implementation."""
    if args.command == "init":
        return cmd_init(args.path)
    if args.command == "quickstart-rag":
        return cmd_quickstart_rag(
            args.path,
            args.text_file,
            actor_id=actor_id,
            actor_type=actor_type,
        )
    if args.command == "create-investigation":
        return cmd_create_investigation(
            args.title,
            args.path,
            args.description,
            actor_id=actor_id,
            actor_type=actor_type,
        )
    if args.command == "ingest-evidence":
        return cmd_ingest_evidence(
            args.file,
            args.investigation,
            args.path,
            args.media_type,
            actor_id=actor_id,
            actor_type=actor_type,
        )
    if args.command == "set-tier":
        return cmd_set_tier(
            args.investigation_uid,
            args.tier,
            args.path,
            args.reason,
            actor_id=actor_id,
            actor_type=actor_type,
        )
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
    if args.command == "replay":
        return cmd_replay(
            args.path,
            getattr(args, "up_to_event", None),
            getattr(args, "up_to_time", None),
        )
    if args.command == "snapshot":
        if args.snapshot_command == "create":
            return cmd_snapshot_create(args.path, args.at_event, args.output)
        if args.snapshot_command == "restore":
            return cmd_snapshot_restore(args.path, args.snapshot)
    if args.command == "verify":
        return cmd_verify(args.path, args.skip_evidence)
    if args.command == "verify-chronicle":
        return cmd_verify_chronicle(args.file, args.no_invariants)
    if args.command == "neo4j-export":
        return cmd_neo4j_export(args.path, args.output)
    if args.command == "neo4j-sync":
        return cmd_neo4j_sync(
            args.path,
            dedupe_evidence_by_content_hash=getattr(args, "dedupe_evidence_by_content_hash", False),
        )
    if args.command == "policy":
        if args.policy_command == "list":
            return cmd_policy_list(args.path)
        if args.policy_command == "export":
            return cmd_policy_export(args.path, args.profile_id, args.output)
        if args.policy_command == "import":
            return cmd_policy_import(args.path, args.file, args.activate)
        if args.policy_command == "compat":
            return cmd_policy_compat(
                args.path,
                args.investigation,
                viewing_profile_id=args.viewing_profile_id,
                built_under_profile_id=args.built_under_profile_id,
                built_under_policy_version=args.built_under_policy_version,
                as_json=args.json,
            )
    return 0
