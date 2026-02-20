"""Timed onboarding gate for Postgres setup.

Runs the doctor + smoke flow, records per-step timings, and fails when:
- any required step fails
- total elapsed time exceeds threshold (default: 600s / 10 minutes)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.store.backend_config import build_postgres_url


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_database_url(explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    return build_postgres_url()


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    if "@" not in rest:
        return database_url
    creds, host = rest.split("@", 1)
    if ":" not in creds:
        return f"{scheme}://***@{host}"
    user = creds.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


def _sanitize_output(text: str, database_url: str, redacted_database_url: str) -> str:
    if not text:
        return text
    return text.replace(database_url, redacted_database_url)


def _run_step(
    command: list[str],
    *,
    timeout_seconds: int,
    database_url: str,
    redacted_database_url: str,
) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    duration = time.monotonic() - started
    return {
        "command": command,
        "return_code": proc.returncode,
        "duration_seconds": round(duration, 3),
        "stdout": _sanitize_output(proc.stdout, database_url, redacted_database_url),
        "stderr": _sanitize_output(proc.stderr, database_url, redacted_database_url),
    }


def evaluate_report(report: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    steps = report.get("steps") or []
    for step in steps:
        if int(step.get("return_code", 1)) != 0:
            reasons.append(f"step_failed:{step.get('name', 'unknown')}")
    total_seconds = float(report.get("total_duration_seconds", 0.0))
    threshold = float(report.get("max_duration_seconds", 0.0))
    if total_seconds > threshold:
        reasons.append("duration_exceeded")
    return (len(reasons) == 0, reasons)


def _run_optional_shell_step(
    *,
    label: str,
    command: str,
    timeout_seconds: int,
    database_url: str,
    redacted_database_url: str,
) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    duration = time.monotonic() - started
    return {
        "name": label,
        "command": command,
        "return_code": proc.returncode,
        "duration_seconds": round(duration, 3),
        "stdout": _sanitize_output(proc.stdout, database_url, redacted_database_url),
        "stderr": _sanitize_output(proc.stderr, database_url, redacted_database_url),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Timed onboarding check for Postgres doctor+smoke flow."
    )
    parser.add_argument(
        "--env-file",
        default=".env.postgres.local",
        help="Optional env file to load before checks (default: .env.postgres.local)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override Postgres URL (default: CHRONICLE_POSTGRES_URL or env-derived URL)",
    )
    parser.add_argument(
        "--output",
        default="reports/postgres_onboarding_timed_check.json",
        help="Output report path (default: reports/postgres_onboarding_timed_check.json)",
    )
    parser.add_argument(
        "--max-duration-seconds",
        type=int,
        default=600,
        help="Max allowed total duration in seconds (default: 600)",
    )
    parser.add_argument(
        "--doctor-timeout-seconds",
        type=int,
        default=120,
        help="Timeout for doctor step (default: 120)",
    )
    parser.add_argument(
        "--smoke-timeout-seconds",
        type=int,
        default=240,
        help="Timeout for smoke step (default: 240)",
    )
    parser.add_argument(
        "--bootstrap-command",
        action="append",
        default=[],
        help="Optional shell command to run before doctor/smoke (can be repeated).",
    )
    parser.add_argument(
        "--teardown-command",
        action="append",
        default=[],
        help="Optional shell command to run at the end (can be repeated).",
    )
    args = parser.parse_args(argv)

    _load_env_file(Path(args.env_file))
    database_url = _resolve_database_url(args.database_url)
    redacted_database_url = _redact_database_url(database_url)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "database_url": redacted_database_url,
        "max_duration_seconds": int(args.max_duration_seconds),
        "steps": [],
    }

    start_total = time.monotonic()
    python_exec = sys.executable
    repo_root = Path(__file__).resolve().parent.parent
    doctor_script = repo_root / "scripts" / "postgres_doctor.py"
    smoke_script = repo_root / "scripts" / "postgres_smoke.py"

    try:
        for idx, command in enumerate(args.bootstrap_command, start=1):
            step = _run_optional_shell_step(
                label=f"bootstrap_{idx}",
                command=command,
                timeout_seconds=max(args.max_duration_seconds, 60),
                database_url=database_url,
                redacted_database_url=redacted_database_url,
            )
            report["steps"].append(step)
            if int(step["return_code"]) != 0:
                raise RuntimeError(f"bootstrap command failed (step {idx})")

        doctor_cmd = [
            python_exec,
            str(doctor_script),
            "--database-url",
            database_url,
            "--json",
        ]
        smoke_cmd = [
            python_exec,
            str(smoke_script),
            "--database-url",
            database_url,
        ]

        doctor_result = _run_step(
            doctor_cmd,
            timeout_seconds=args.doctor_timeout_seconds,
            database_url=database_url,
            redacted_database_url=redacted_database_url,
        )
        doctor_result["name"] = "postgres_doctor"
        report["steps"].append(doctor_result)

        smoke_result = _run_step(
            smoke_cmd,
            timeout_seconds=args.smoke_timeout_seconds,
            database_url=database_url,
            redacted_database_url=redacted_database_url,
        )
        smoke_result["name"] = "postgres_smoke"
        report["steps"].append(smoke_result)
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        for idx, command in enumerate(args.teardown_command, start=1):
            step = _run_optional_shell_step(
                label=f"teardown_{idx}",
                command=command,
                timeout_seconds=max(args.max_duration_seconds, 60),
                database_url=database_url,
                redacted_database_url=redacted_database_url,
            )
            report["steps"].append(step)

    report["total_duration_seconds"] = round(time.monotonic() - start_total, 3)
    report["ended_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok, reasons = evaluate_report(report)
    report["ok"] = ok
    report["failure_reasons"] = reasons
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if ok:
        print("[PASS] Postgres onboarding timed check passed")
        print(
            f"       total_duration_seconds={report['total_duration_seconds']} "
            f"(threshold={report['max_duration_seconds']})"
        )
        print(f"       report={output_path}")
        return 0

    print("[FAIL] Postgres onboarding timed check failed")
    print(
        f"       total_duration_seconds={report['total_duration_seconds']} "
        f"(threshold={report['max_duration_seconds']})"
    )
    if reasons:
        print(f"       reasons={','.join(reasons)}")
    print(f"       report={output_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
