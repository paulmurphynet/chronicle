"""
Score a scenario validation run: conformance (chronicle-verify) + rubric checks
on the exported .chronicle (investigations, claims, support links, tensions).
Runs are produced by the rule-based driver (no AI/LLM).

Run from repo root:
  PYTHONPATH=. python3 scripts/ai_validation/score_run.py [path/to/export.chronicle]
  PYTHONPATH=. python3 scripts/ai_validation/score_run.py --scenario journalism_conflict

If no path is given, uses scripts/ai_validation/out/<scenario_id>.chronicle.
Exit 0 only if conformance and all rubric checks pass.
"""

import argparse
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = SCRIPT_DIR / "scenarios"
OUT_DIR = SCRIPT_DIR / "out"
REPORTS_DIR = SCRIPT_DIR / "reports"


def load_scenario_rubric(scenario_id: str) -> dict:
    """Load rubric from scenario JSON. Returns default if missing."""
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    default = {
        "min_investigations": 1,
        "min_claims": 2,
        "min_support_links": 1,
        "require_tension": True,
    }
    if not path.is_file():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("rubric", default)


def verify_conformance(chronicle_path: Path) -> tuple[bool, list[dict]]:
    """Run chronicle-verify on the file. Returns (all_passed, list of {name, passed, detail})."""
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    raw = verify_chronicle_file(chronicle_path, run_invariants=True)
    results = [{"name": name, "passed": passed, "detail": detail} for name, passed, detail in raw]
    all_passed = all(r["passed"] for r in results)
    return all_passed, results


def run_rubric(chronicle_path: Path, rubric: dict) -> tuple[bool, list[dict]]:
    """Open the .chronicle ZIP, query the DB for rubric checks. Returns (all_passed, list of {name, passed, detail})."""
    if not chronicle_path.is_file() or chronicle_path.suffix != ".chronicle":
        return False, [{"name": "file", "passed": False, "detail": f"Not a .chronicle file: {chronicle_path}"}]

    try:
        with zipfile.ZipFile(chronicle_path, "r") as zf:
            if "chronicle.db" not in zf.namelist():
                return False, [{"name": "rubric_db", "passed": False, "detail": "ZIP missing chronicle.db"}]
            with tempfile.TemporaryDirectory(prefix="chronicle_score_") as tmp:
                db_path = Path(tmp) / "chronicle.db"
                db_path.write_bytes(zf.read("chronicle.db"))
                conn = sqlite3.connect(str(db_path))
                try:
                    cur = conn.execute("SELECT COUNT(*) FROM investigation")
                    n_inv = cur.fetchone()[0]
                    cur = conn.execute("SELECT COUNT(*) FROM claim")
                    n_claims = cur.fetchone()[0]
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM evidence_link WHERE link_type = 'SUPPORTS'"
                    )
                    n_support = cur.fetchone()[0]
                    cur = conn.execute("SELECT COUNT(*) FROM tension")
                    n_tensions = cur.fetchone()[0]
                finally:
                    conn.close()
    except (zipfile.BadZipFile, sqlite3.OperationalError) as e:
        return False, [{"name": "rubric_db", "passed": False, "detail": str(e)}]

    results = []
    all_passed = True
    min_inv = rubric.get("min_investigations", 1)
    if n_inv >= min_inv:
        results.append({"name": "investigations", "passed": True, "detail": f">= {min_inv}: {n_inv}"})
    else:
        results.append({"name": "investigations", "passed": False, "detail": f"got {n_inv}, need >= {min_inv}"})
        all_passed = False

    min_claims = rubric.get("min_claims", 2)
    if n_claims >= min_claims:
        results.append({"name": "claims", "passed": True, "detail": f">= {min_claims}: {n_claims}"})
    else:
        results.append({"name": "claims", "passed": False, "detail": f"got {n_claims}, need >= {min_claims}"})
        all_passed = False

    min_support = rubric.get("min_support_links", 1)
    if n_support >= min_support:
        results.append({"name": "support_links", "passed": True, "detail": f">= {min_support}: {n_support}"})
    else:
        results.append({"name": "support_links", "passed": False, "detail": f"got {n_support}, need >= {min_support}"})
        all_passed = False

    if rubric.get("require_tension", True):
        if n_tensions >= 1:
            results.append({"name": "tension", "passed": True, "detail": f"at least one: {n_tensions}"})
        else:
            results.append({"name": "tension", "passed": False, "detail": "got 0; conflict scenario requires at least one tension"})
            all_passed = False
    else:
        results.append({"name": "tension", "passed": True, "detail": f"{n_tensions} (not required)"})

    return all_passed, results


def _summary_and_suggestion(
    scenario_id: str,
    conformance_ok: bool,
    rubric_ok: bool,
    rubric_results: list[dict],
) -> tuple[str, str]:
    """Human-readable summary and optional to-do suggestion."""
    if conformance_ok and rubric_ok:
        return "All checks passed.", ""
    parts = []
    if not conformance_ok:
        parts.append("Conformance failed (chronicle-verify).")
    if not rubric_ok:
        failed = [r for r in rubric_results if not r["passed"]]
        part = "Rubric failed: " + "; ".join(r["name"] + ": " + r["detail"] for r in failed)
        parts.append(part)
    summary = " ".join(parts)
    suggestion = (
        f"Scenario validation: {scenario_id} — {summary} Add to docs/to_do.md or fix app/playbook/scenario as needed."
    )
    return summary, suggestion


def write_failure_report(
    scenario_id: str,
    chronicle_path: Path | None,
    conformance_ok: bool,
    conformance_results: list[dict],
    rubric_ok: bool,
    rubric_results: list[dict],
    error: str | None = None,
) -> None:
    """Write last_run.json and last_run.md to REPORTS_DIR on failure or error."""
    summary, suggestion = _summary_and_suggestion(
        scenario_id, conformance_ok, rubric_ok, rubric_results
    )
    if error:
        summary = error
        suggestion = f"Scenario validation: {scenario_id} — {error}"

    report = {
        "scenario_id": scenario_id,
        "chronicle_path": str(chronicle_path) if chronicle_path else None,
        "error": error,
        "conformance_passed": conformance_ok,
        "conformance_checks": conformance_results,
        "rubric_passed": rubric_ok,
        "rubric_checks": rubric_results,
        "summary": summary,
        "suggestion": suggestion,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "last_run.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_lines = [
        "# Scenario validation failure report",
        "",
        f"**Scenario:** {scenario_id}",
        f"**Chronicle path:** {chronicle_path or 'N/A'}",
        "",
        f"**Summary:** {summary}",
        "",
        "## Conformance",
    ]
    for r in conformance_results:
        status = "PASS" if r["passed"] else "FAIL"
        md_lines.append(f"- [{status}] {r['name']}: {r['detail']}")
    md_lines.extend(["", "## Rubric"])
    for r in rubric_results:
        status = "PASS" if r["passed"] else "FAIL"
        md_lines.append(f"- [{status}] {r['name']}: {r['detail']}")
    md_lines.extend(["", "## Suggestion", "", "```", suggestion, "```"])
    md_path = REPORTS_DIR / "last_run.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score a scenario validation run: conformance + rubric. On failure writes reports/last_run.json and last_run.md.",
    )
    parser.add_argument(
        "chronicle_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to .chronicle export. Default: out/<scenario_id>.chronicle",
    )
    parser.add_argument(
        "--scenario",
        default="journalism_conflict",
        help="Scenario id for rubric and default path. Default: journalism_conflict",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write failure report to reports/last_run.*",
    )
    args = parser.parse_args()

    path = args.chronicle_path
    if path is None:
        path = OUT_DIR / f"{args.scenario}.chronicle"

    path = path.resolve()
    if not path.is_file():
        err_msg = f"File not found: {path}"
        print(err_msg, file=sys.stderr)
        print(
            "Run: PYTHONPATH=. python3 scripts/ai_validation/run_agent.py --scenario " + args.scenario,
            file=sys.stderr,
        )
        if not args.no_report:
            write_failure_report(
                args.scenario,
                path,
                conformance_ok=False,
                conformance_results=[],
                rubric_ok=False,
                rubric_results=[],
                error=err_msg,
            )
            print(f"Failure report written to {REPORTS_DIR / 'last_run.json'} and last_run.md", file=sys.stderr)
        return 2

    rubric = load_scenario_rubric(args.scenario)

    print("Conformance (chronicle-verify):")
    conformance_ok, conformance_results = verify_conformance(path)
    for r in conformance_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}: {r['detail']}")
    if not conformance_ok:
        print("Conformance failed.", file=sys.stderr)
        if not args.no_report:
            rubric_ok, rubric_results = run_rubric(path, rubric)
            write_failure_report(
                args.scenario,
                path,
                conformance_ok=False,
                conformance_results=conformance_results,
                rubric_ok=rubric_ok,
                rubric_results=rubric_results,
            )
            print(f"Failure report written to {REPORTS_DIR / 'last_run.json'} and last_run.md", file=sys.stderr)
        return 1

    print("Rubric:")
    rubric_ok, rubric_results = run_rubric(path, rubric)
    for r in rubric_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}: {r['detail']}")
    if not rubric_ok:
        print("Rubric failed.", file=sys.stderr)
        if not args.no_report:
            write_failure_report(
                args.scenario,
                path,
                conformance_ok=True,
                conformance_results=conformance_results,
                rubric_ok=False,
                rubric_results=rubric_results,
            )
            print(f"Failure report written to {REPORTS_DIR / 'last_run.json'} and last_run.md", file=sys.stderr)
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
