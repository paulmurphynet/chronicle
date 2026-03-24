"""
Propose Learn guide annotations from successful scenario validation run traces (Phase 9).
Runs are from the rule-based driver (no AI/LLM).

Reads trace JSON from reports/traces/ (or a given path), compares to guides.json,
and prints suggested example lines or tips for human review. Human approves and
edits chronicle/api/static/learn/guides.json to accept.

Run from repo root:
  PYTHONPATH=. python3 scripts/ai_validation/propose_learn_from_trace.py
  PYTHONPATH=. python3 scripts/ai_validation/propose_learn_from_trace.py reports/traces/journalism_conflict.json

Output: markdown to stdout with one section per trace and bullet suggestions.
"""

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TRACES_DIR = SCRIPT_DIR / "reports" / "traces"
GUIDES_JSON = REPO_ROOT / "chronicle" / "api" / "static" / "learn" / "guides.json"

# Map scenario_id to Learn guide vertical id
SCENARIO_TO_VERTICAL: dict[str, str] = {
    "journalism_conflict": "journalism",
    "journalism_single_claim": "journalism",
    "legal_conflict": "legal",
    "legal_single_claim": "legal",
    "compliance_single_claim": "compliance",
    "fact_checking_single_claim": "fact-checking",
    "internal_investigations_single_claim": "internal-investigations",
    "due_diligence_single_claim": "due-diligence",
    "academic_single_claim": "academic",
}


def _vertical_for_scenario(scenario_id: str) -> str | None:
    if scenario_id in SCENARIO_TO_VERTICAL:
        return SCENARIO_TO_VERTICAL[scenario_id]
    for prefix, vertical in SCENARIO_TO_VERTICAL.items():
        if scenario_id.startswith(prefix.split("_")[0]):
            return vertical
    return None


def load_guides() -> dict:
    if not GUIDES_JSON.is_file():
        return {"guides": []}
    return json.loads(GUIDES_JSON.read_text(encoding="utf-8"))


def load_trace(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def propose_for_trace(trace: dict, guides_data: dict) -> list[str]:
    """Return list of suggestion lines for this trace."""
    suggestions: list[str] = []
    scenario_id = trace.get("scenario_id", "?")
    steps = trace.get("steps") or []
    vertical = _vertical_for_scenario(scenario_id)
    if not vertical:
        suggestions.append(
            f"Unknown scenario '{scenario_id}'; no vertical mapping. Add to SCENARIO_TO_VERTICAL."
        )
        return suggestions

    guide = next((g for g in guides_data.get("guides", []) if g.get("id") == vertical), None)
    if not guide:
        suggestions.append(f"Guide '{vertical}' not found in guides.json.")
        return suggestions

    guide_steps = guide.get("steps") or []
    step_actions: dict[int, list[dict]] = {}
    for s in steps:
        learn_step = s.get("learn_step")
        if learn_step is not None:
            step_actions.setdefault(learn_step, []).append(s)

    for step_index in sorted(step_actions.keys()):
        actions = step_actions[step_index]
        if step_index < 1 or step_index > len(guide_steps):
            continue
        gs = guide_steps[step_index - 1]
        title = gs.get("title", "")
        has_example = bool(gs.get("example"))

        action_summary = "; ".join(
            a.get("action", "")
            + (f" (count={a.get('count')})" if a.get("count") is not None else "")
            for a in actions
        )
        if has_example:
            suggestions.append(
                f"- **Step {step_index} ({title}):** Run had: {action_summary}. Guide already has an example; consider aligning wording with run (e.g. same counts)."
            )
        else:
            tip = f"In successful runs: {action_summary}."
            suggestions.append(
                f'- **Step {step_index} ({title}):** Run had: {action_summary}. Consider adding `example`: "{tip}" (edit guides.json and approve).'
            )

    # Cross-step tip: order of actions
    if any(s.get("action") == "link_support" for s in steps) and any(
        s.get("action") == "propose_claims" for s in steps
    ):
        suggestions.append(
            '- **Tip (steps 3–4):** Successful runs do propose_claims then link_support before Defensibility. Consider adding a one-line tip to step 3 or 4: "Link support to claims before checking defensibility."'
        )

    return suggestions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Propose Learn guide annotations from run traces. Output: markdown suggestions for human review."
    )
    parser.add_argument(
        "trace_paths",
        nargs="*",
        type=Path,
        default=None,
        help="Trace JSON file(s). Default: all reports/traces/*.json",
    )
    parser.add_argument(
        "--guides",
        type=Path,
        default=GUIDES_JSON,
        help=f"Path to guides.json. Default: {GUIDES_JSON.relative_to(REPO_ROOT)}",
    )
    args = parser.parse_args()

    guides_data = (
        json.loads(args.guides.read_text(encoding="utf-8"))
        if args.guides.is_file()
        else {"guides": []}
    )

    paths = args.trace_paths
    if not paths:
        paths = sorted(TRACES_DIR.glob("*.json")) if TRACES_DIR.is_dir() else []

    if not paths:
        print(
            "No trace files found. Run: PYTHONPATH=. python3 scripts/ai_validation/run_agent.py --scenario <id> --trace"
        )
        return 0

    print("# Learn guide suggestions from scenario validation traces\n")
    print(
        "Review and approve; then edit `chronicle/api/static/learn/guides.json` to add or adjust `example` / tips.\n"
    )

    for path in paths:
        trace = load_trace(path)
        if not trace or not trace.get("success"):
            continue
        scenario_id = trace.get("scenario_id", path.stem)
        suggestions = propose_for_trace(trace, guides_data)
        if not suggestions:
            continue
        print(f"## Scenario: {scenario_id}\n")
        for line in suggestions:
            print(line)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
