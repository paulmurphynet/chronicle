#!/usr/bin/env python3
"""Build a reproducible evidence pack for whitepaper claims."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_generic_export_module = import_module("chronicle.store.commands.generic_export")
build_c2pa_compatibility_export = _generic_export_module.build_c2pa_compatibility_export
build_claimreview_export = _generic_export_module.build_claimreview_export
build_ro_crate_export = _generic_export_module.build_ro_crate_export
build_standards_jsonld_export = _generic_export_module.build_standards_jsonld_export
build_vc_data_integrity_export = _generic_export_module.build_vc_data_integrity_export
validate_standards_jsonld_export = _generic_export_module.validate_standards_jsonld_export
create_project = import_module("chronicle.store.project").create_project
ChronicleSession = import_module("chronicle.store.session").ChronicleSession

PACK_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _tail(text: str, lines: int = 20) -> str:
    parts = text.splitlines()
    return "\n".join(parts[-lines:]) if parts else ""


def _run_cmd(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    elapsed = round(time.perf_counter() - start, 3)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "duration_s": elapsed,
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "stdout_full": proc.stdout,
    }


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _component_benchmark(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "benchmark"
    work.mkdir(parents=True, exist_ok=True)
    results_path = work / "benchmark_defensibility_results.json"
    trust_report_path = work / "trust_progress_report.json"

    cmd_benchmark = [
        sys.executable,
        str(repo_root / "scripts/benchmark_data/run_defensibility_benchmark.py"),
        "--mode",
        "session",
        "--output",
        str(results_path),
    ]
    benchmark_run = _run_cmd(cmd_benchmark, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "benchmark",
        "status": "failed",
        "commands": [benchmark_run],
        "artifacts": {"results": str(results_path)},
    }
    if benchmark_run["returncode"] != 0:
        result["error"] = "benchmark_failed"
        return result

    cmd_trust = [
        sys.executable,
        str(repo_root / "scripts/benchmark_data/trust_progress_report.py"),
        "--results",
        str(results_path),
    ]
    trust_run = _run_cmd(cmd_trust, cwd=repo_root)
    result["commands"].append(trust_run)
    if trust_run["returncode"] != 0:
        result["error"] = "trust_progress_failed"
        return result

    try:
        trust_payload = json.loads((trust_run.get("stdout_full") or "").strip())
    except json.JSONDecodeError as exc:
        result["error"] = f"trust_progress_parse_failed:{exc}"
        return result

    _write_json(trust_report_path, trust_payload)
    result["artifacts"]["trust_report"] = str(trust_report_path)
    result["summary"] = trust_payload.get("summary", {})
    result["status"] = "passed"
    return result


def _component_workflows(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "reference_workflows"
    work.mkdir(parents=True, exist_ok=True)
    report_path = work / "reference_workflow_report.json"
    cmd = [
        sys.executable,
        str(repo_root / "scripts/run_reference_workflows.py"),
        "--only",
        "benchmark",
        "legal",
        "history",
        "--output-dir",
        str(work),
    ]
    run = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "workflows",
        "status": "failed",
        "commands": [run],
        "artifacts": {"reference_workflow_report": str(report_path)},
    }
    if run["returncode"] != 0:
        result["error"] = "reference_workflows_failed"
        return result
    if not report_path.is_file():
        result["error"] = f"missing_reference_workflow_report:{report_path}"
        return result
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["error"] = f"reference_workflow_report_parse_failed:{exc}"
        return result

    result["summary"] = report.get("summary", {})
    result["status"] = "passed"
    return result


def _component_standards(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "standards_profiles"
    project_path = work / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    create_project(project_path)

    with ChronicleSession(project_path) as session:
        _, inv_uid = session.create_investigation(
            "Whitepaper evidence pack standards example",
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        _, ev_support = session.ingest_evidence(
            inv_uid,
            b"Supporting evidence body",
            "text/plain",
            original_filename="support.txt",
            metadata={
                "c2pa_claim_id": "urn:uuid:c2pa-claim-1",
                "c2pa_assertion_id": "assertion-1",
                "c2pa_manifest_digest": "sha256:abcd",
                "c2pa_verification_status": "verified",
            },
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        _, span_support = session.anchor_span(
            inv_uid,
            ev_support,
            "text_offset",
            {"start_char": 0, "end_char": 23},
            quote="Supporting evidence body",
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        _, ev_challenge = session.ingest_evidence(
            inv_uid,
            b"Challenging evidence body",
            "text/plain",
            original_filename="challenge.txt",
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        _, span_challenge = session.anchor_span(
            inv_uid,
            ev_challenge,
            "text_offset",
            {"start_char": 0, "end_char": 23},
            quote="Challenging evidence body",
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Primary claim for standards example.",
            initial_type="SEF",
            actor_id="whitepaper-pack",
            actor_type="tool",
            verification_level="verified_credential",
            attestation_ref="urn:vc:claim-1",
        )
        _, other_claim_uid = session.propose_claim(
            inv_uid,
            "Competing claim for tension modeling.",
            initial_type="SEF",
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        session.link_support(
            inv_uid,
            span_support,
            claim_uid,
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        session.link_challenge(
            inv_uid,
            span_challenge,
            claim_uid,
            actor_id="whitepaper-pack",
            actor_type="tool",
        )
        session.declare_tension(
            inv_uid,
            claim_uid,
            other_claim_uid,
            tension_kind="contradiction",
            notes="Intentional contradiction for profile export coverage.",
            actor_id="whitepaper-pack",
            actor_type="tool",
            workspace="forge",
        )
        _, source_uid = session.register_source(
            inv_uid,
            "Standards Example Source",
            source_type="organization",
            actor_id="whitepaper-pack",
            actor_type="tool",
            workspace="forge",
        )
        session.link_evidence_to_source(
            ev_support,
            source_uid,
            relationship="provided_by",
            actor_id="whitepaper-pack",
            actor_type="tool",
            workspace="forge",
        )
        _, artifact_uid = session.create_artifact(
            inv_uid,
            "Standards evidence packet",
            artifact_type="report",
            actor_id="whitepaper-pack",
            actor_type="tool",
            workspace="forge",
            verification_level="verified_credential",
            attestation_ref="urn:vc:artifact-1",
        )
        session.create_checkpoint(
            inv_uid,
            [claim_uid],
            artifact_refs=[artifact_uid],
            reason="Checkpoint for whitepaper evidence pack example",
            certifying_org_id="chronicle-lab",
            certified_at="2026-02-20T00:00:00Z",
            actor_id="whitepaper-pack",
            actor_type="tool",
            workspace="vault",
            verification_level="claimed",
            attestation_ref="urn:vc:checkpoint-1",
        )

        standards_jsonld = build_standards_jsonld_export(session.read_model, inv_uid)
        claimreview = build_claimreview_export(
            session.read_model,
            session.get_defensibility_score,
            inv_uid,
            publisher_name="Chronicle Whitepaper Pack",
        )
        ro_crate = build_ro_crate_export(session.read_model, inv_uid)
        c2pa_disabled = build_c2pa_compatibility_export(
            session.read_model,
            inv_uid,
            verification_enabled=False,
        )
        c2pa_enabled = build_c2pa_compatibility_export(
            session.read_model,
            inv_uid,
            verification_enabled=True,
        )
        vc_disabled = build_vc_data_integrity_export(
            session.read_model,
            inv_uid,
            verification_enabled=False,
        )
        vc_enabled = build_vc_data_integrity_export(
            session.read_model,
            inv_uid,
            verification_enabled=True,
        )
        standards_errors = validate_standards_jsonld_export(standards_jsonld)
        chronicle_path = work / "sample_investigation.chronicle"
        session.export_investigation(inv_uid, chronicle_path)

    artifacts = {
        "standards_jsonld_export": _write_json(
            work / "standards_jsonld_export.json", standards_jsonld
        ),
        "standards_jsonld_validation": _write_json(
            work / "standards_jsonld_validation.json",
            {"errors": standards_errors},
        ),
        "claimreview_export": _write_json(work / "claimreview_export.json", claimreview),
        "ro_crate_export": _write_json(work / "ro_crate_export.json", ro_crate),
        "c2pa_export_disabled": _write_json(work / "c2pa_export_disabled.json", c2pa_disabled),
        "c2pa_export_metadata_only": _write_json(
            work / "c2pa_export_metadata_only.json", c2pa_enabled
        ),
        "vc_export_disabled": _write_json(work / "vc_export_disabled.json", vc_disabled),
        "vc_export_metadata_only": _write_json(work / "vc_export_metadata_only.json", vc_enabled),
        "sample_chronicle": str(chronicle_path),
    }
    result: dict[str, Any] = {
        "name": "standards",
        "status": "passed" if not standards_errors else "failed",
        "commands": [],
        "artifacts": artifacts,
        "summary": {
            "investigation_uid": inv_uid,
            "jsonld_node_count": len(standards_jsonld.get("@graph", [])),
            "claimreview_count": len(claimreview.get("itemListElement", [])),
            "ro_crate_node_count": len(ro_crate.get("@graph", [])),
            "c2pa_evidence_assertions": len(c2pa_enabled.get("evidence_assertions", [])),
            "vc_claim_attestations": len(vc_enabled.get("attestations", {}).get("claims", [])),
        },
    }
    if standards_errors:
        result["error"] = f"standards_jsonld_validation_failed:{standards_errors}"
    return result


def _component_verifier(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "verifier"
    work.mkdir(parents=True, exist_ok=True)
    report_path = work / "verification_report.json"

    sample_chronicle = run_dir / "standards_profiles" / "sample_investigation.chronicle"
    if not sample_chronicle.is_file():
        project_path = work / "project"
        create_project(project_path)
        with ChronicleSession(project_path) as session:
            _, inv_uid = session.create_investigation(
                "Verifier evidence sample",
                actor_id="whitepaper-pack",
                actor_type="tool",
            )
            session.ingest_evidence(
                inv_uid,
                b"Verifier evidence sample body",
                "text/plain",
                original_filename="verifier.txt",
                actor_id="whitepaper-pack",
                actor_type="tool",
            )
            session.propose_claim(
                inv_uid,
                "Verifier sample claim.",
                actor_id="whitepaper-pack",
                actor_type="tool",
            )
            sample_chronicle = work / "sample_investigation.chronicle"
            session.export_investigation(inv_uid, sample_chronicle)

    cmd_verify = [
        sys.executable,
        "-m",
        "tools.verify_chronicle",
        str(sample_chronicle),
        "--json",
        "--summary",
    ]
    verify_run = _run_cmd(cmd_verify, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "verifier",
        "status": "failed",
        "commands": [verify_run],
        "artifacts": {
            "sample_chronicle": str(sample_chronicle),
            "verification_report": str(report_path),
        },
    }
    if verify_run["returncode"] != 0:
        result["error"] = "verifier_failed"
        return result

    try:
        verify_payload = json.loads((verify_run.get("stdout_full") or "").strip())
    except json.JSONDecodeError as exc:
        result["error"] = f"verification_report_parse_failed:{exc}"
        return result

    _write_json(report_path, verify_payload)
    result["summary"] = {
        "verified": bool(verify_payload.get("verified")),
        "checks": len(verify_payload.get("checks", [])),
    }
    if not verify_payload.get("verified"):
        result["error"] = "verification_checks_failed"
        return result
    result["status"] = "passed"
    return result


COMPONENT_RUNNERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "benchmark": _component_benchmark,
    "workflows": _component_workflows,
    "standards": _component_standards,
    "verifier": _component_verifier,
}


def _default_output_dir(repo_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return repo_root / "whitepaper_evidence_runs" / stamp


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    choices = sorted(COMPONENT_RUNNERS.keys())
    parser = argparse.ArgumentParser(
        description="Build a whitepaper reproducibility evidence pack."
    )
    parser.add_argument(
        "--components",
        nargs="*",
        choices=choices,
        default=choices,
        help="Pack components to build",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write evidence pack artifacts",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after first failed component",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print final manifest to stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = REPO_ROOT
    run_dir = (args.output_dir or _default_output_dir(repo_root)).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    component_names = args.components if args.components else sorted(COMPONENT_RUNNERS.keys())

    manifest: dict[str, Any] = {
        "schema_version": PACK_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "components_requested": component_names,
        "components": [],
    }

    failed_count = 0
    for name in component_names:
        runner = COMPONENT_RUNNERS[name]
        try:
            item = runner(repo_root, run_dir)
        except Exception as exc:  # defensive: manifest should still be written
            item = {"name": name, "status": "failed", "error": f"exception:{exc}"}
        manifest["components"].append(item)
        if item.get("status") != "passed":
            failed_count += 1
            if args.fail_fast:
                break

    manifest["completed_at"] = _utc_now()
    manifest["summary"] = {
        "total": len(manifest["components"]),
        "passed": sum(1 for c in manifest["components"] if c.get("status") == "passed"),
        "failed": sum(1 for c in manifest["components"] if c.get("status") == "failed"),
    }

    commands = []
    for component in manifest["components"]:
        for command in component.get("commands", []):
            commands.append(command.get("command"))
    manifest["commands"] = [cmd for cmd in commands if isinstance(cmd, list)]

    manifest_path = run_dir / "evidence_pack_manifest.json"
    _write_json(manifest_path, manifest)
    print(f"Wrote whitepaper evidence pack manifest: {manifest_path}")
    if args.stdout_json:
        print(json.dumps(manifest, indent=2))

    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
