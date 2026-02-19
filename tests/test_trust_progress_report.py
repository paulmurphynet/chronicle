from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_module = import_module("scripts.benchmark_data.trust_progress_report")
main = _module.main
summarize_rows = _module.summarize_rows


def _write_results(path: Path, rows: list[dict]) -> None:
    payload = {"benchmark": "test", "results": rows}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_summarize_rows_counts_and_rates() -> None:
    rows = [
        {
            "query_id": "q1",
            "error": None,
            "metrics": {
                "provenance_quality": "strong",
                "corroboration": {"support_count": 2},
                "contradiction_status": "none",
            },
        },
        {
            "query_id": "q2",
            "error": None,
            "metrics": {
                "provenance_quality": "weak",
                "corroboration": {"support_count": 0},
                "contradiction_status": "open",
            },
        },
        {
            "query_id": "q3",
            "error": "no_claim",
            "metrics": None,
        },
    ]
    summary = summarize_rows(rows)
    assert summary["counts"]["total_claims"] == 3
    assert summary["counts"]["scored_claims"] == 2
    assert summary["counts"]["unscored_claims"] == 1
    assert summary["counts"]["unsupported_scored_claims"] == 1
    assert summary["rates"]["strict_unsupported_rate"] == 0.5
    assert summary["rates"]["unscored_rate"] == 0.3333
    assert summary["rates"]["effective_unsupported_rate"] == 0.6667
    assert summary["provenance_distribution"]["strong"] == 0.5
    assert summary["provenance_distribution"]["weak"] == 0.5


def test_main_returns_zero_when_reduction_meets_threshold(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"

    _write_results(
        baseline,
        [
            {
                "error": None,
                "metrics": {"corroboration": {"support_count": 0}},
            },
            {"error": "no_claim", "metrics": None},
        ],
    )
    _write_results(
        current,
        [
            {
                "error": None,
                "metrics": {"corroboration": {"support_count": 1}},
            },
            {
                "error": None,
                "metrics": {"corroboration": {"support_count": 1}},
            },
        ],
    )

    code = main(
        [
            "--results",
            str(current),
            "--baseline",
            str(baseline),
            "--min-effective-unsupported-reduction",
            "0.5",
        ]
    )
    assert code == 0


def test_main_returns_one_when_effective_rate_exceeds_threshold(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    _write_results(
        current,
        [
            {"error": "no_claim", "metrics": None},
            {"error": None, "metrics": {"corroboration": {"support_count": 0}}},
        ],
    )
    code = main(
        [
            "--results",
            str(current),
            "--max-effective-unsupported-rate",
            "0.5",
        ]
    )
    assert code == 1
