"""
Generate a deterministic history/research sample .chronicle file.
Scenario: conflicting archival interpretations for a completion year with explicit tension.

Run from repository root:
  PYTHONPATH=. python3 scripts/verticals/history/generate_sample.py
  PYTHONPATH=. python3 scripts/verticals/history/generate_sample.py --output /tmp/sample_history.chronicle
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_history.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "history_research.json"

EVIDENCE_1 = "Archive letter dated 1865 states the bridge was completed in 1864."
EVIDENCE_2 = "Newspaper digest from 1863 reports the bridge opened in 1862."
EVIDENCE_3 = "Archivist note: completion year remains contested pending additional records."


def _span_for_quote(text: str, quote: str) -> dict[str, int]:
    start = text.index(quote)
    end = start + len(quote)
    return {"start_char": start, "end_char": end}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic history/research sample .chronicle."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output .chronicle path (default: frontend/public/sample_history.chronicle)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    args = _parse_args(argv)
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_history_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation("History sample: contested completion year")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            evidence = session.read_model.list_evidence_by_investigation(inv_uid)
            ev1_uid = evidence[0].evidence_uid
            ev2_uid = evidence[1].evidence_uid

            _, claim_a_uid = session.propose_claim(inv_uid, "Bridge completion year was 1864.")
            _, claim_b_uid = session.propose_claim(inv_uid, "Bridge completion year was 1862.")
            session.propose_claim(
                inv_uid,
                "Completion year remains contested and should be presented with caveats.",
            )

            quote_a = "bridge was completed in 1864"
            quote_b = "bridge opened in 1862"

            _, span_a_uid = session.anchor_span(
                inv_uid,
                ev1_uid,
                "text_offset",
                _span_for_quote(EVIDENCE_1, quote_a),
                quote=quote_a,
            )
            session.link_support(inv_uid, span_a_uid, claim_a_uid)

            _, span_b_uid = session.anchor_span(
                inv_uid,
                ev2_uid,
                "text_offset",
                _span_for_quote(EVIDENCE_2, quote_b),
                quote=quote_b,
            )
            session.link_support(inv_uid, span_b_uid, claim_b_uid)

            session.declare_tension(inv_uid, claim_a_uid, claim_b_uid, workspace="forge")

            out = tmp_path / "sample_history.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
