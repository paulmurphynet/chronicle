#!/usr/bin/env python3
"""Run reference workflows and emit a consolidated JSON report."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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


def _copy_if_exists(src: Path, dest: Path) -> str | None:
    if not src.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return str(dest)


def _workflow_journalism(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    cmd = [sys.executable, str(repo_root / "scripts/verticals/journalism/generate_sample.py")]
    command = _run_cmd(cmd, cwd=repo_root)
    sample_path = repo_root / "frontend/public/sample.chronicle"
    result: dict[str, Any] = {
        "name": "journalism",
        "status": "failed",
        "commands": [command],
        "artifacts": {},
    }
    if command["returncode"] != 0:
        result["error"] = "generator_failed"
        return result
    if not sample_path.is_file():
        result["error"] = f"missing_sample_file:{sample_path}"
        return result

    checks = verify_chronicle_file(sample_path, run_invariants=True)
    failed = [name for name, passed, _detail in checks if not passed]
    result["verification_checks"] = [
        {"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks
    ]
    copied = _copy_if_exists(sample_path, run_dir / "journalism" / "sample.chronicle")
    if copied:
        result["artifacts"]["sample_chronicle"] = copied
    if failed:
        result["error"] = f"verification_failed:{failed}"
        return result

    result["status"] = "passed"
    return result


def _workflow_legal(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    sample_path = run_dir / "legal" / "sample_legal.chronicle"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "scripts/verticals/legal/generate_sample.py"),
        "--output",
        str(sample_path),
    ]
    command = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "legal",
        "status": "failed",
        "commands": [command],
        "artifacts": {"sample_chronicle": str(sample_path)},
    }
    if command["returncode"] != 0:
        result["error"] = "generator_failed"
        return result
    if not sample_path.is_file():
        result["error"] = f"missing_sample_file:{sample_path}"
        return result

    checks = verify_chronicle_file(sample_path, run_invariants=True)
    failed = [name for name, passed, _detail in checks if not passed]
    result["verification_checks"] = [
        {"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks
    ]
    if failed:
        result["error"] = f"verification_failed:{failed}"
        return result

    result["status"] = "passed"
    return result


def _workflow_history(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    sample_path = run_dir / "history" / "sample_history.chronicle"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "scripts/verticals/history/generate_sample.py"),
        "--output",
        str(sample_path),
    ]
    command = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "history",
        "status": "failed",
        "commands": [command],
        "artifacts": {"sample_chronicle": str(sample_path)},
    }
    if command["returncode"] != 0:
        result["error"] = "generator_failed"
        return result
    if not sample_path.is_file():
        result["error"] = f"missing_sample_file:{sample_path}"
        return result

    checks = verify_chronicle_file(sample_path, run_invariants=True)
    failed = [name for name, passed, _detail in checks if not passed]
    result["verification_checks"] = [
        {"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks
    ]
    if failed:
        result["error"] = f"verification_failed:{failed}"
        return result

    result["status"] = "passed"
    return result


def _workflow_messy(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    sample_path = run_dir / "messy" / "sample_messy.chronicle"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "scripts/verticals/messy/generate_sample.py"),
        "--output",
        str(sample_path),
    ]
    command = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "messy",
        "status": "failed",
        "commands": [command],
        "artifacts": {"sample_chronicle": str(sample_path)},
    }
    if command["returncode"] != 0:
        result["error"] = "generator_failed"
        return result
    if not sample_path.is_file():
        result["error"] = f"missing_sample_file:{sample_path}"
        return result

    checks = verify_chronicle_file(sample_path, run_invariants=True)
    failed = [name for name, passed, _detail in checks if not passed]
    result["verification_checks"] = [
        {"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks
    ]
    if failed:
        result["error"] = f"verification_failed:{failed}"
        return result

    result["status"] = "passed"
    return result


def _workflow_samples(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "samples"
    work.mkdir(parents=True, exist_ok=True)
    report_path = work / "sample_quality_report.json"
    cmd = [
        sys.executable,
        str(repo_root / "scripts/verticals/check_sample_quality.py"),
        "--output-report",
        str(report_path),
    ]
    run = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "samples",
        "status": "failed",
        "commands": [run],
        "artifacts": {"sample_quality_report": str(report_path)},
    }
    if run["returncode"] != 0:
        result["error"] = "sample_quality_check_failed"
        return result
    if not report_path.is_file():
        result["error"] = f"missing_sample_quality_report:{report_path}"
        return result
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result["error"] = f"sample_quality_report_parse_failed:{e}"
        return result
    result["summary"] = payload.get("summary")
    result["status"] = "passed"
    return result


def _workflow_readiness(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    work = run_dir / "readiness"
    work.mkdir(parents=True, exist_ok=True)
    sample_path = work / "sample_compliance.chronicle"
    project_path = work / "project"
    report_path = work / "readiness_gate_report.json"

    cmd_generate = [
        sys.executable,
        str(repo_root / "scripts/verticals/compliance/generate_sample.py"),
        "--output",
        str(sample_path),
    ]
    run_generate = _run_cmd(cmd_generate, cwd=repo_root)

    result: dict[str, Any] = {
        "name": "readiness",
        "status": "failed",
        "commands": [run_generate],
        "artifacts": {
            "sample_chronicle": str(sample_path),
            "project_path": str(project_path),
            "readiness_report": str(report_path),
        },
    }
    if run_generate["returncode"] != 0:
        result["error"] = "sample_generator_failed"
        return result
    if not sample_path.is_file():
        result["error"] = f"missing_sample_file:{sample_path}"
        return result

    checks = verify_chronicle_file(sample_path, run_invariants=True)
    failed = [name for name, passed, _detail in checks if not passed]
    result["verification_checks"] = [
        {"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks
    ]
    if failed:
        result["error"] = f"sample_verification_failed:{failed}"
        return result

    cmd_init = [sys.executable, "-m", "chronicle.cli.main", "init", str(project_path)]
    run_init = _run_cmd(cmd_init, cwd=repo_root)
    result["commands"].append(run_init)
    if run_init["returncode"] != 0:
        result["error"] = "project_init_failed"
        return result

    cmd_import = [
        sys.executable,
        "-m",
        "chronicle.cli.main",
        "import",
        str(sample_path),
        "--path",
        str(project_path),
    ]
    run_import = _run_cmd(cmd_import, cwd=repo_root)
    result["commands"].append(run_import)
    if run_import["returncode"] != 0:
        result["error"] = "sample_import_failed"
        return result

    from chronicle.store.session import ChronicleSession

    with ChronicleSession(project_path) as session:
        invs = session.read_model.list_investigations()
        if not invs:
            result["error"] = "no_investigations_after_import"
            return result
        investigation_uid = invs[0].investigation_uid

    cmd_gate = [
        sys.executable,
        str(repo_root / "scripts/review_readiness_gate.py"),
        "--path",
        str(project_path),
        "--investigation-uid",
        investigation_uid,
        "--max-unresolved-tensions",
        "1",
        "--output",
        str(report_path),
    ]
    run_gate = _run_cmd(cmd_gate, cwd=repo_root)
    result["commands"].append(run_gate)
    if run_gate["returncode"] != 0:
        result["error"] = "readiness_gate_failed"
        return result
    if not report_path.is_file():
        result["error"] = f"missing_readiness_report:{report_path}"
        return result

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result["error"] = f"readiness_report_parse_failed:{e}"
        return result

    result["summary"] = {
        "investigation_uid": investigation_uid,
        "status": payload.get("status"),
        "unresolved_tensions_count": (payload.get("metrics") or {}).get(
            "unresolved_tensions_count"
        ),
        "policy_deltas_count": (payload.get("metrics") or {}).get("policy_deltas_count"),
    }
    if payload.get("status") != "passed":
        result["error"] = "readiness_report_status_failed"
        return result

    result["status"] = "passed"
    return result


def _workflow_benchmark(repo_root: Path, run_dir: Path) -> dict[str, Any]:
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
    trust_proc_start = time.perf_counter()
    trust_proc = subprocess.run(cmd_trust, cwd=repo_root, capture_output=True, text=True)
    trust_run = {
        "command": cmd_trust,
        "returncode": trust_proc.returncode,
        "duration_s": round(time.perf_counter() - trust_proc_start, 3),
        "stdout_tail": _tail(trust_proc.stdout),
        "stderr_tail": _tail(trust_proc.stderr),
    }
    result["commands"].append(trust_run)
    if trust_run["returncode"] != 0:
        result["error"] = "trust_report_failed"
        return result

    try:
        trust_payload = json.loads((trust_proc.stdout or "").strip())
    except json.JSONDecodeError as e:
        result["error"] = f"trust_report_parse_failed:{e}"
        return result

    trust_report_path.write_text(json.dumps(trust_payload, indent=2), encoding="utf-8")
    result["artifacts"]["trust_report"] = str(trust_report_path)
    result["summary"] = trust_payload.get("summary")
    result["status"] = "passed"
    return result


def _workflow_compliance(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    work = run_dir / "compliance"
    work.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "scripts/compliance_report_from_rag.py"),
        "--mode",
        "session",
        "--output-dir",
        str(work),
    ]
    run = _run_cmd(cmd, cwd=repo_root)
    report_path = work / "report" / "audit_report.json"
    result: dict[str, Any] = {
        "name": "compliance",
        "status": "failed",
        "commands": [run],
        "artifacts": {"audit_report": str(report_path)},
    }
    if run["returncode"] != 0:
        result["error"] = "compliance_script_failed"
        return result
    if not report_path.is_file():
        result["error"] = f"missing_audit_report:{report_path}"
        return result
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result["summary"] = {
        "investigation_uid": report.get("investigation_uid"),
        "claim_count": len(report.get("claims", [])),
        "evidence_count": len(report.get("evidence_uids", [])),
    }
    result["status"] = "passed"
    return result


def _workflow_neo4j(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(repo_root / "scripts/check_neo4j_contract.py")]
    run = _run_cmd(cmd, cwd=repo_root)
    result: dict[str, Any] = {
        "name": "neo4j",
        "status": "passed" if run["returncode"] == 0 else "failed",
        "commands": [run],
        "artifacts": {},
    }
    if run["returncode"] != 0:
        result["error"] = "neo4j_contract_check_failed"
    return result


WORKFLOW_RUNNERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "journalism": _workflow_journalism,
    "legal": _workflow_legal,
    "history": _workflow_history,
    "messy": _workflow_messy,
    "samples": _workflow_samples,
    "readiness": _workflow_readiness,
    "benchmark": _workflow_benchmark,
    "compliance": _workflow_compliance,
    "neo4j": _workflow_neo4j,
}


def _resolve_workflows(only: list[str], skip: list[str]) -> list[str]:
    selected = only[:] if only else list(WORKFLOW_RUNNERS.keys())
    return [name for name in selected if name not in set(skip)]


def _default_output_dir(repo_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return repo_root / "reference_workflow_runs" / stamp


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    choices = sorted(WORKFLOW_RUNNERS.keys())
    parser = argparse.ArgumentParser(
        description="Run Chronicle reference workflows and summarize results."
    )
    parser.add_argument("--only", nargs="*", choices=choices, default=[])
    parser.add_argument("--skip", nargs="*", choices=choices, default=[])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write workflow artifacts and report",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after first failed workflow",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print final report JSON to stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    run_dir = (args.output_dir or _default_output_dir(repo_root)).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    workflow_names = _resolve_workflows(args.only, args.skip)

    report: dict[str, Any] = {
        "started_at": _utc_now(),
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "workflows_requested": workflow_names,
        "workflows": [],
    }

    failed_count = 0
    for name in workflow_names:
        runner = WORKFLOW_RUNNERS[name]
        try:
            item = runner(repo_root, run_dir)
        except Exception as e:  # defensive catch to keep report complete
            item = {"name": name, "status": "failed", "error": f"exception:{e}"}
        report["workflows"].append(item)
        if item.get("status") != "passed":
            failed_count += 1
            if args.fail_fast:
                break

    report["completed_at"] = _utc_now()
    total = len(report["workflows"])
    passed = sum(1 for wf in report["workflows"] if wf.get("status") == "passed")
    failed = sum(1 for wf in report["workflows"] if wf.get("status") == "failed")
    skipped = sum(1 for wf in report["workflows"] if wf.get("status") == "skipped")
    report["summary"] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }

    report_path = run_dir / "reference_workflow_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote workflow report: {report_path}")
    if args.stdout_json:
        print(json.dumps(report, indent=2))

    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
