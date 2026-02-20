#!/usr/bin/env python3
"""Validate completeness and realism of vertical sample .chronicle artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession
from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class SampleSpec:
    name: str
    script_path: Path
    expected_policy_id: str
    extra_min_counts: dict[str, int]


SAMPLE_SPECS: dict[str, SampleSpec] = {
    "journalism": SampleSpec(
        name="journalism",
        script_path=REPO_ROOT / "scripts/verticals/journalism/generate_sample.py",
        expected_policy_id="policy_investigative_journalism",
        extra_min_counts={},
    ),
    "legal": SampleSpec(
        name="legal",
        script_path=REPO_ROOT / "scripts/verticals/legal/generate_sample.py",
        expected_policy_id="policy_legal",
        extra_min_counts={},
    ),
    "history": SampleSpec(
        name="history",
        script_path=REPO_ROOT / "scripts/verticals/history/generate_sample.py",
        expected_policy_id="policy_history_research",
        extra_min_counts={},
    ),
    "compliance": SampleSpec(
        name="compliance",
        script_path=REPO_ROOT / "scripts/verticals/compliance/generate_sample.py",
        expected_policy_id="policy_compliance",
        extra_min_counts={},
    ),
    "messy": SampleSpec(
        name="messy",
        script_path=REPO_ROOT / "scripts/verticals/messy/generate_sample.py",
        expected_policy_id="policy_compliance",
        extra_min_counts={
            "redaction_signal_count": 1,
            "supersession_count": 1,
            "temporalized_claim_count": 2,
        },
    ),
}

MIN_COUNTS: dict[str, int] = {
    "claim_count": 3,
    "typed_claim_count": 3,
    "evidence_count": 3,
    "source_count": 2,
    "source_with_independence_notes_count": 2,
    "evidence_source_link_count": 3,
    "support_link_count": 3,
    "support_with_rationale_count": 3,
    "challenge_link_count": 1,
    "challenge_with_rationale_count": 1,
    "tension_count": 1,
    "redacted_evidence_count": 0,
    "redaction_signal_count": 0,
    "supersession_count": 0,
    "temporalized_claim_count": 0,
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check quality/completeness of Chronicle vertical samples.")
    parser.add_argument("--only", nargs="*", choices=sorted(SAMPLE_SPECS.keys()), default=[])
    parser.add_argument(
        "--output-report",
        type=Path,
        default=None,
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print full report JSON to stdout.",
    )
    return parser.parse_args(argv)


def _run_generator(script_path: Path, output_path: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(script_path), "--output", str(output_path)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _manifest_for(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as zf:
        return json.loads(zf.read("manifest.json"))


def _verification_for(path: Path) -> dict[str, Any]:
    checks = verify_chronicle_file(path, run_invariants=True)
    failures = [name for name, passed, _detail in checks if not passed]
    return {
        "checks": [{"name": name, "passed": passed, "detail": detail} for name, passed, detail in checks],
        "failures": failures,
    }


def _select_investigation_uid(session: ChronicleSession) -> str:
    investigations = session.read_model.list_investigations()
    if not investigations:
        raise RuntimeError("No investigations after import")
    if len(investigations) == 1:
        return investigations[0].investigation_uid
    return sorted(investigations, key=lambda i: (i.created_at or "", i.investigation_uid))[-1].investigation_uid


def _metrics_for(path: Path) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="chronicle_sample_quality_project_") as tmp:
        project = Path(tmp)
        create_project(project)
        with ChronicleSession(project) as session:
            session.import_investigation(path)
            inv_uid = _select_investigation_uid(session)
            rm = session.read_model
            claims = rm.list_claims_by_type(investigation_uid=inv_uid, include_withdrawn=True, limit=500)
            evidence_items = rm.list_evidence_by_investigation(inv_uid)
            sources = rm.list_sources_by_investigation(inv_uid)
            tensions = rm.list_tensions(investigation_uid=inv_uid, limit=500)

            support_links = [link for c in claims for link in rm.get_support_for_claim(c.claim_uid)]
            challenge_links = [link for c in claims for link in rm.get_challenges_for_claim(c.claim_uid)]
            evidence_source_links = [
                link
                for ev in evidence_items
                for link in rm.list_evidence_source_links(ev.evidence_uid)
            ]
            supersession_uids = {
                s.supersession_uid
                for ev in evidence_items
                for s in rm.list_supersessions_for_evidence(ev.evidence_uid)
            }

            return {
                "claim_count": len(claims),
                "typed_claim_count": sum(
                    1 for c in claims if c.claim_type is not None and c.claim_type.strip() != "UNKNOWN"
                ),
                "evidence_count": len(evidence_items),
                "source_count": len(sources),
                "source_with_independence_notes_count": sum(
                    1
                    for s in sources
                    if s.independence_notes is not None and s.independence_notes.strip() != ""
                ),
                "evidence_source_link_count": len(evidence_source_links),
                "support_link_count": len(support_links),
                "support_with_rationale_count": sum(
                    1 for link in support_links if link.rationale is not None and link.rationale.strip() != ""
                ),
                "challenge_link_count": len(challenge_links),
                "challenge_with_rationale_count": sum(
                    1 for link in challenge_links if link.rationale is not None and link.rationale.strip() != ""
                ),
                "tension_count": len(tensions),
                "redacted_evidence_count": sum(
                    1
                    for ev in evidence_items
                    if ev.redaction_reason is not None and ev.redaction_reason.strip() != ""
                ),
                "redaction_signal_count": sum(
                    1 for c in claims if "redact" in (c.claim_text or "").lower()
                ),
                "supersession_count": len(supersession_uids),
                "temporalized_claim_count": sum(
                    1 for c in claims if c.temporal_json is not None and c.temporal_json.strip() != ""
                ),
            }


def _issues_for(
    metrics: dict[str, int],
    expected_policy_id: str,
    observed_policy_id: str | None,
    min_counts: dict[str, int],
) -> list[str]:
    issues: list[str] = []
    if observed_policy_id != expected_policy_id:
        issues.append(
            f"manifest built_under_policy_id mismatch: expected={expected_policy_id!r} got={observed_policy_id!r}"
        )
    for key, min_value in min_counts.items():
        observed = metrics.get(key, 0)
        if observed < min_value:
            issues.append(f"{key} below minimum: expected>={min_value} got={observed}")
    return issues


def _run_one(spec: SampleSpec, output_path: Path) -> dict[str, Any]:
    generator = _run_generator(spec.script_path, output_path)
    result: dict[str, Any] = {
        "sample": spec.name,
        "output_path": str(output_path),
        "generator": generator,
        "status": "failed",
        "issues": [],
    }
    if generator["returncode"] != 0:
        result["issues"].append("generator_failed")
        return result
    if not output_path.is_file():
        result["issues"].append(f"missing_output:{output_path}")
        return result

    verification = _verification_for(output_path)
    result["verification"] = verification
    if verification["failures"]:
        result["issues"].append(f"verification_failed:{verification['failures']}")
        return result

    manifest = _manifest_for(output_path)
    metrics = _metrics_for(output_path)
    result["manifest"] = {
        "investigation_uid": manifest.get("investigation_uid"),
        "built_under_policy_id": manifest.get("built_under_policy_id"),
        "built_under_policy_version": manifest.get("built_under_policy_version"),
    }
    result["metrics"] = metrics
    min_counts = dict(MIN_COUNTS)
    min_counts.update(spec.extra_min_counts)
    result["issues"] = _issues_for(
        metrics,
        spec.expected_policy_id,
        manifest.get("built_under_policy_id"),
        min_counts,
    )
    if not result["issues"]:
        result["status"] = "passed"
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    selected = args.only or sorted(SAMPLE_SPECS.keys())

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_quality_outputs_") as tmp:
        output_root = Path(tmp)
        results = []
        for name in selected:
            spec = SAMPLE_SPECS[name]
            output_path = output_root / f"{name}.chronicle"
            results.append(_run_one(spec, output_path))

    failed = [r for r in results if r["status"] != "passed"]
    report = {
        "summary": {
            "total": len(results),
            "failed": len(failed),
            "passed": len(results) - len(failed),
        },
        "results": results,
    }

    if args.output_report is not None:
        out = args.output_report.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote sample quality report to {out}")

    if args.stdout_json:
        print(json.dumps(report, indent=2))
    else:
        for row in results:
            status = row["status"].upper()
            print(f"[{status}] {row['sample']}")
            for issue in row["issues"]:
                print(f"  - {issue}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
