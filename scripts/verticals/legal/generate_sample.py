"""Generate a deterministic legal sample .chronicle file."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_legal.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "legal.json"

EVIDENCE_1 = (
    "Master Service Agreement Clause 7 states delivery shall occur by March 1, 2024 "
    "absent a signed amendment."
)
EVIDENCE_2 = (
    "Amendment 2 signed later states the delivery date is April 15, 2024 "
    "and supersedes prior timing language."
)
EVIDENCE_3 = (
    "Case strategy note: contract timing terms conflict; filing must describe uncertainty "
    "until controlling instrument is confirmed."
)


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

            _, ev1_uid = session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            _, ev2_uid = session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            _, ev3_uid = session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            _, src1_uid = session.register_source(
                inv_uid,
                "MSA Clause 7 document",
                "document",
                independence_notes="Original contract text independent from amendment process.",
                reliability_notes="Signed primary contractual record.",
                workspace="forge",
            )
            _, src2_uid = session.register_source(
                inv_uid,
                "Amendment 2 instrument",
                "document",
                independence_notes="Later negotiated instrument with distinct execution date.",
                reliability_notes="Signed amendment referencing supersession language.",
                workspace="forge",
            )
            _, src3_uid = session.register_source(
                inv_uid,
                "Litigation strategy memo",
                "organization",
                independence_notes="Internal legal synthesis separate from source contracts.",
                reliability_notes="Attorney work product summary; not itself controlling law.",
                workspace="forge",
            )
            session.link_evidence_to_source(ev1_uid, src1_uid, relationship="provided_by", workspace="forge")
            session.link_evidence_to_source(ev2_uid, src2_uid, relationship="provided_by", workspace="forge")
            session.link_evidence_to_source(ev3_uid, src3_uid, relationship="authored_by", workspace="forge")

            _, claim_a_uid = session.propose_claim(inv_uid, "Delivery due March 1, 2024.")
            _, claim_b_uid = session.propose_claim(inv_uid, "Delivery due April 15, 2024.")
            _, claim_c_uid = session.propose_claim(
                inv_uid,
                "Conflicting delivery terms must be resolved before filing.",
            )
            session.type_claim(
                claim_a_uid,
                "SAC",
                rationale="Supported by base contract language but contested by amendment.",
                workspace="forge",
            )
            session.type_claim(
                claim_b_uid,
                "SAC",
                rationale="Supported by later amendment but contested by base contract text.",
                workspace="forge",
            )
            session.type_claim(
                claim_c_uid,
                "INFERENCE",
                rationale="Derived compliance posture from conflicting contractual terms.",
                workspace="forge",
            )
            session.temporalize_claim(
                claim_b_uid,
                {
                    "known_range_start": "2024-04-15T00:00:00Z",
                    "known_range_end": "2024-04-15T23:59:59Z",
                    "temporal_confidence": 0.85,
                    "time_notes": "Explicit date in signed amendment.",
                },
                workspace="forge",
            )

            quote_a = "delivery shall occur by March 1, 2024"
            quote_b = "delivery date is April 15, 2024"
            quote_c = "timing terms conflict; filing must describe uncertainty"

            _, span_a_uid = session.anchor_span(
                inv_uid,
                ev1_uid,
                "text_offset",
                _span_for_quote(EVIDENCE_1, quote_a),
                quote=quote_a,
            )
            session.link_support(
                inv_uid,
                span_a_uid,
                claim_a_uid,
                rationale="Base contract clause sets the earlier deadline.",
            )

            _, span_b_uid = session.anchor_span(
                inv_uid,
                ev2_uid,
                "text_offset",
                _span_for_quote(EVIDENCE_2, quote_b),
                quote=quote_b,
            )
            session.link_support(
                inv_uid,
                span_b_uid,
                claim_b_uid,
                rationale="Amendment language states superseding later date.",
            )
            _, span_c_uid = session.anchor_span(
                inv_uid,
                ev3_uid,
                "text_offset",
                _span_for_quote(EVIDENCE_3, quote_c),
                quote=quote_c,
            )
            session.link_support(
                inv_uid,
                span_c_uid,
                claim_c_uid,
                rationale="Counsel note explicitly records unresolved contractual conflict.",
            )
            session.link_challenge(
                inv_uid,
                span_b_uid,
                claim_a_uid,
                rationale="Later signed amendment undermines earlier deadline certainty.",
                workspace="forge",
            )
            session.link_challenge(
                inv_uid,
                span_a_uid,
                claim_b_uid,
                rationale="Original agreement conflicts with amended date interpretation.",
                workspace="forge",
            )

            session.declare_tension(
                inv_uid,
                claim_a_uid,
                claim_b_uid,
                tension_kind="contradiction",
                notes="Mutually inconsistent delivery deadlines in governing documents.",
                workspace="forge",
            )

            out = tmp_path / "sample_legal.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
