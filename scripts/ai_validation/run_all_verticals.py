"""
Run all scenario validation scenarios (rule-based; no AI/LLM) and report pass/fail
per scenario. Exit 0 only if all pass. For use before release or in CI when enabled.

Run from repo root:
  PYTHONPATH=. python3 scripts/ai_validation/run_all_verticals.py

Output: one line per scenario (e.g. "journalism_conflict: pass") then a summary.
Uses --no-report so failure reports are not written for each run (run score_run.py
manually on a failed scenario to get reports/last_run.*).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AI_VALIDATION_DIR = REPO_ROOT / "scripts" / "ai_validation"
RUN_AGENT = AI_VALIDATION_DIR / "run_agent.py"
SCORE_RUN = AI_VALIDATION_DIR / "score_run.py"

# Roster: scenario ids that run_agent.py supports. Add new scenarios here and in run_agent.py.
SCENARIOS = [
    "journalism_conflict",
    "journalism_single_claim",
    "legal_conflict",
    "legal_single_claim",
    "compliance_single_claim",
    "fact_checking_single_claim",
    "internal_investigations_single_claim",
    "due_diligence_single_claim",
    "academic_single_claim",
]


def run_one(scenario_id: str, chronicle_path: Path, env: dict) -> tuple[bool, str]:
    """Run scenario driver then scorer for one scenario. Returns (passed, message)."""
    driver_result = subprocess.run(
        [
            sys.executable,
            str(RUN_AGENT),
            "--scenario",
            scenario_id,
            "--output",
            str(chronicle_path),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if driver_result.returncode != 0:
        return False, "driver failed: " + (
            driver_result.stderr or driver_result.stdout or "unknown"
        ).strip()[:200]

    score_result = subprocess.run(
        [
            sys.executable,
            str(SCORE_RUN),
            "--scenario",
            scenario_id,
            "--no-report",
            str(chronicle_path),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if score_result.returncode != 0:
        msg = (score_result.stderr or score_result.stdout or "unknown").strip()
        # Use last line or first line that says "failed"
        for line in msg.splitlines():
            if "failed" in line.lower() or "FAIL" in line:
                msg = line.strip()
                break
        return False, "scorer failed: " + msg[:200]
    return True, "pass"


def main() -> int:
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)}
    results: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory(prefix="chronicle_run_all_") as tmp:
        tmp_path = Path(tmp)
        for scenario_id in SCENARIOS:
            chronicle_path = tmp_path / f"{scenario_id}.chronicle"
            passed, message = run_one(scenario_id, chronicle_path, env)
            results.append((scenario_id, passed, message))
            status = "pass" if passed else "fail"
            print(f"  {scenario_id}: {status}" + ("" if passed else f" ({message})"))

    passed_count = sum(1 for _, p, _ in results if p)
    total = len(results)
    print("")
    if passed_count == total:
        print(f"All {total} scenarios passed.")
        return 0
    print(f"{passed_count}/{total} passed; {total - passed_count} failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
