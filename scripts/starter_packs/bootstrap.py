#!/usr/bin/env python3
"""Bootstrap opinionated Chronicle starter packs with deterministic fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_export_import_module = import_module("chronicle.store.export_import")
import_investigation = _export_import_module.import_investigation
_project_module = import_module("chronicle.store.project")
create_project = _project_module.create_project
project_exists = _project_module.project_exists
ChronicleSession = import_module("chronicle.store.session").ChronicleSession
_generic_export = import_module("chronicle.store.commands.generic_export")
build_standards_jsonld_export = _generic_export.build_standards_jsonld_export
build_claimreview_export = _generic_export.build_claimreview_export
build_ro_crate_export = _generic_export.build_ro_crate_export
POLICY_FILENAME = import_module("chronicle.core.policy").POLICY_FILENAME


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
    }


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


_PACK_CONFIG: dict[str, dict[str, str]] = {
    "journalism": {
        "profile": "journalism.json",
        "generator_script": "scripts/verticals/journalism/generate_sample.py",
        "sample_name": "sample_journalism.chronicle",
        "title": "Journalism starter pack",
    },
    "legal": {
        "profile": "legal.json",
        "generator_script": "scripts/verticals/legal/generate_sample.py",
        "sample_name": "sample_legal.chronicle",
        "title": "Legal starter pack",
    },
    "audit": {
        "profile": "compliance.json",
        "generator_script": "scripts/verticals/compliance/generate_sample.py",
        "sample_name": "sample_audit.chronicle",
        "title": "Audit starter pack",
    },
}


def _copy_policy_profile(pack: str, project_path: Path) -> Path:
    config = _PACK_CONFIG[pack]
    src = REPO_ROOT / "docs" / "policy-profiles" / config["profile"]
    if not src.is_file():
        raise FileNotFoundError(f"Missing policy profile for pack {pack!r}: {src}")
    dst = project_path / POLICY_FILENAME
    shutil.copy(src, dst)
    return dst


def _generate_fixture(pack: str, fixture_path: Path) -> dict[str, Any]:
    config = _PACK_CONFIG[pack]
    cmd = [
        sys.executable,
        str(REPO_ROOT / config["generator_script"]),
        "--output",
        str(fixture_path),
    ]
    return _run_cmd(cmd, cwd=REPO_ROOT)


def _build_reports_and_exports(project_path: Path, output_dir: Path) -> dict[str, Any]:
    reports_dir = output_dir / "reports"
    exports_dir = output_dir / "exports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    with ChronicleSession(project_path) as session:
        investigations = session.read_model.list_investigations(limit=100)
        if not investigations:
            raise ValueError("No investigations found after fixture import")
        inv_uid = investigations[-1].investigation_uid

        review_packet = session.get_review_packet(
            inv_uid,
            include_reasoning_briefs=False,
            decision_limit=500,
            limit_claims=200,
        )
        audit_bundle = session.get_audit_export_bundle(
            inv_uid,
            include_full_trail=False,
            limit_claims=200,
        )
        standards_jsonld = build_standards_jsonld_export(session.read_model, inv_uid)
        claimreview = build_claimreview_export(
            session.read_model,
            session.get_defensibility_score,
            inv_uid,
            publisher_name="Chronicle Starter Pack",
        )
        ro_crate = build_ro_crate_export(session.read_model, inv_uid)

    artifacts = {
        "review_packet": _write_json(reports_dir / "review_packet.json", review_packet),
        "audit_export_bundle": _write_json(reports_dir / "audit_export_bundle.json", audit_bundle),
        "standards_jsonld_export": _write_json(
            exports_dir / "standards_jsonld_export.json", standards_jsonld
        ),
        "claimreview_export": _write_json(exports_dir / "claimreview_export.json", claimreview),
        "ro_crate_export": _write_json(exports_dir / "ro_crate_export.json", ro_crate),
    }
    summary = {
        "investigation_uid": inv_uid,
        "claims_in_snapshot": len(audit_bundle.get("defensibility_snapshot") or []),
        "review_packet_claims": len((review_packet.get("audit_export_bundle") or {}).get("claims", [])),
    }
    return {"artifacts": artifacts, "summary": summary}


def bootstrap_starter_pack(
    *,
    pack: str,
    project_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if pack not in _PACK_CONFIG:
        raise ValueError(f"Unknown pack {pack!r}; expected one of {sorted(_PACK_CONFIG)}")

    project_path = project_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = output_dir / "fixtures" / _PACK_CONFIG[pack]["sample_name"]
    fixture_path.parent.mkdir(parents=True, exist_ok=True)

    created_project = False
    if not project_exists(project_path):
        project_path.mkdir(parents=True, exist_ok=True)
        create_project(project_path)
        created_project = True
    copied_policy = _copy_policy_profile(pack, project_path)

    generator_run = _generate_fixture(pack, fixture_path)
    result: dict[str, Any] = {
        "schema_version": 1,
        "pack": pack,
        "status": "failed",
        "generated_at": _utc_now(),
        "project_path": str(project_path),
        "output_dir": str(output_dir),
        "created_project": created_project,
        "commands": [generator_run],
        "artifacts": {
            "policy_profile": str(copied_policy),
            "fixture_chronicle": str(fixture_path),
        },
    }
    if generator_run["returncode"] != 0:
        result["error"] = "fixture_generation_failed"
        return result
    if not fixture_path.is_file():
        result["error"] = f"missing_fixture:{fixture_path}"
        return result

    import_investigation(fixture_path, project_path)
    result["commands"].append(
        {
            "command": ["import_investigation", str(fixture_path), str(project_path)],
            "returncode": 0,
            "duration_s": 0.0,
            "stdout_tail": "",
            "stderr_tail": "",
        }
    )

    payload = _build_reports_and_exports(project_path, output_dir)
    result["artifacts"].update(payload["artifacts"])
    result["summary"] = payload["summary"]
    if int(result["summary"]["claims_in_snapshot"]) <= 0:
        result["error"] = "no_defensibility_snapshot_claims"
        return result
    result["status"] = "passed"
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap Chronicle starter packs (journalism, legal, audit)."
    )
    parser.add_argument(
        "--pack",
        required=True,
        choices=sorted(_PACK_CONFIG.keys()),
        help="Starter pack to bootstrap.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Project path to create or update.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated reports/exports/fixtures (default: <path>/starter_pack_artifacts/<pack>).",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print full result JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    default_out = args.path / "starter_pack_artifacts" / args.pack
    out_dir = args.output_dir or default_out

    try:
        result = bootstrap_starter_pack(
            pack=args.pack,
            project_path=args.path,
            output_dir=out_dir,
        )
    except Exception as exc:
        result = {
            "schema_version": 1,
            "pack": args.pack,
            "status": "failed",
            "error": f"exception:{exc}",
            "generated_at": _utc_now(),
            "project_path": str(args.path.resolve()),
            "output_dir": str(out_dir.resolve()),
            "commands": [],
            "artifacts": {},
        }

    manifest_path = (out_dir.resolve() / "starter_pack_manifest.json")
    _write_json(manifest_path, result)
    print(f"Wrote starter pack manifest: {manifest_path}")
    if args.stdout_json:
        print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
