#!/usr/bin/env python3
"""Integration contract harness for JSON/CSV/Markdown and signed .chronicle bundle flows."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.store.commands.generic_export import (
    build_generic_export_csv_zip,
    build_generic_export_json,
    validate_generic_export_csv_zip,
    validate_generic_export_json,
)
from chronicle.store.commands.reasoning_brief import reasoning_brief_to_markdown
from chronicle.store.export_import import (
    export_signed_investigation_bundle,
    import_signed_investigation_bundle,
    verify_signed_investigation_bundle,
)
from chronicle.store.project import create_project, project_exists
from chronicle.store.session import ChronicleSession
from tools.verify_chronicle.verify_chronicle import verify_chronicle_file


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _seed(project_path: Path) -> tuple[str, str]:
    with ChronicleSession(project_path) as session:
        _, inv_uid = session.create_investigation(
            "Integration export contract",
            actor_id="contract-harness",
            actor_type="tool",
        )
        session.set_tier(
            inv_uid,
            "forge",
            reason="integration export contract requires tension coverage",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, ev_support = session.ingest_evidence(
            inv_uid,
            b"Ledger confirms a quarter-end accounting entry.",
            "text/plain",
            original_filename="ledger.txt",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, support_span = session.anchor_span(
            inv_uid,
            ev_support,
            "text_offset",
            {"start_char": 0, "end_char": 12},
            quote="Ledger confirms",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, ev_challenge = session.ingest_evidence(
            inv_uid,
            b"Delivery receipt indicates fulfillment after quarter close.",
            "text/plain",
            original_filename="delivery.txt",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, challenge_span = session.anchor_span(
            inv_uid,
            ev_challenge,
            "text_offset",
            {"start_char": 0, "end_char": 16},
            quote="Delivery receipt",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Revenue timing needs exception review.",
            actor_id="contract-harness",
            actor_type="tool",
        )
        _, counter_uid = session.propose_claim(
            inv_uid,
            "Revenue timing is unambiguously resolved.",
            actor_id="contract-harness",
            actor_type="tool",
        )
        session.link_support(
            inv_uid, support_span, claim_uid, actor_id="contract-harness", actor_type="tool"
        )
        session.link_challenge(
            inv_uid, challenge_span, claim_uid, actor_id="contract-harness", actor_type="tool"
        )
        session.declare_tension(
            inv_uid,
            claim_uid,
            counter_uid,
            tension_kind="contradiction",
            actor_id="contract-harness",
            actor_type="tool",
        )
    return inv_uid, claim_uid


def run(project_path: Path, output_dir: Path) -> dict[str, Any]:
    if not project_exists(project_path):
        project_path.mkdir(parents=True, exist_ok=True)
        create_project(project_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    inv_uid, claim_uid = _seed(project_path)
    target_import_path = output_dir / "signed_bundle_import_target"
    if not project_exists(target_import_path):
        target_import_path.mkdir(parents=True, exist_ok=True)
        create_project(target_import_path)

    with ChronicleSession(project_path) as session:
        generic_json = build_generic_export_json(session.read_model, inv_uid)
        generic_csv = build_generic_export_csv_zip(session.read_model, inv_uid)
        brief = session.get_reasoning_brief(claim_uid)
        if brief is None:
            raise ValueError("Failed to build reasoning brief for seeded claim")
        markdown = reasoning_brief_to_markdown(brief)
        export_path = output_dir / "sample_investigation.chronicle"
        session.export_investigation(inv_uid, export_path)

    generic_json_path = output_dir / "generic_export.json"
    generic_csv_path = output_dir / "generic_export_csv.zip"
    brief_markdown_path = output_dir / "reasoning_brief.md"
    generic_json_path.write_text(json.dumps(generic_json, indent=2), encoding="utf-8")
    generic_csv_path.write_bytes(generic_csv)
    brief_markdown_path.write_text(markdown, encoding="utf-8")

    signed_bundle_path = export_signed_investigation_bundle(
        project_path,
        inv_uid,
        output_dir / "sample_investigation_signed.zip",
        signer="chronicle-integration-contract",
    )
    signed_manifest = verify_signed_investigation_bundle(signed_bundle_path)
    import_signed_investigation_bundle(signed_bundle_path, target_import_path)

    with ChronicleSession(target_import_path) as imported:
        imported_investigations = imported.read_model.list_investigations(limit=20)

    verifier_rows = verify_chronicle_file(export_path, run_invariants=True)
    failed_verifier = [row for row in verifier_rows if row[1] is not True]
    json_errors = validate_generic_export_json(generic_json)
    csv_errors = validate_generic_export_csv_zip(generic_csv)
    markdown_ok = "## Claim" in markdown and "## Defensibility" in markdown
    import_ok = any(x.investigation_uid == inv_uid for x in imported_investigations)

    report = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "status": "passed",
        "investigation_uid": inv_uid,
        "claim_uid": claim_uid,
        "checks": {
            "generic_json_contract_errors": json_errors,
            "generic_csv_contract_errors": csv_errors,
            "markdown_contract_ok": markdown_ok,
            "chronicle_verifier_failures": failed_verifier,
            "signed_bundle_signature_status": signed_manifest.get("signature", {}).get("status"),
            "signed_bundle_import_ok": import_ok,
        },
        "artifacts": {
            "generic_json": str(generic_json_path),
            "generic_csv_zip": str(generic_csv_path),
            "reasoning_brief_markdown": str(brief_markdown_path),
            "chronicle_export": str(export_path),
            "signed_bundle_zip": str(signed_bundle_path),
        },
    }
    if json_errors or csv_errors or not markdown_ok or failed_verifier or not import_ok:
        report["status"] = "failed"
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run integration export/import contract harness.")
    parser.add_argument(
        "--project-path", type=Path, required=True, help="Source Chronicle project path"
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="Output directory for artifacts"
    )
    parser.add_argument("--stdout-json", action="store_true", help="Print report JSON to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run(args.project_path, args.output_dir)
    report_path = args.output_dir.resolve() / "integration_export_contract_report.json"
    _write_json(report_path, report)
    print(f"Wrote integration export contract report: {report_path}")
    if args.stdout_json:
        print(json.dumps(report, indent=2))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
