"""
Generate a deterministic legal sample .chronicle file.
Scenario: conflicting contract delivery dates (March 1 vs April 15) with an explicit tension.

Run from repository root:
  PYTHONPATH=. python3 scripts/verticals/legal/generate_sample.py
  PYTHONPATH=. python3 scripts/verticals/legal/generate_sample.py --output /tmp/sample_legal.chronicle
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_legal.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "legal.json"

EVIDENCE_1 = "Master Service Agreement Clause 7 states delivery shall occur by March 1, 2024."
EVIDENCE_2 = "Amendment 2 signed later states the delivery date is April 15, 2024."
EVIDENCE_3 = "Review note: delivery date terms conflict and must be resolved before legal filing."


def _span_for_quote(text: str, quote: str) -> dict[str, int]:
    start = text.index(quote)
    end = start + len(quote)
    return {"start_char": start, "end_char": end}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic legal sample .chronicle.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output .chronicle path (default: frontend/public/sample_legal.chronicle)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    args = _parse_args(argv)
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_legal_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation("Legal sample: delivery date conflict")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            evidence = session.read_model.list_evidence_by_investigation(inv_uid)
            ev1_uid = evidence[0].evidence_uid
            ev2_uid = evidence[1].evidence_uid

            _, claim_a_uid = session.propose_claim(inv_uid, "Delivery due March 1, 2024.")
            _, claim_b_uid = session.propose_claim(inv_uid, "Delivery due April 15, 2024.")
            session.propose_claim(
                inv_uid,
                "Conflicting delivery terms must be resolved before filing.",
            )

            quote_a = "delivery shall occur by March 1, 2024"
            quote_b = "delivery date is April 15, 2024"

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

            out = tmp_path / "sample_legal.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
