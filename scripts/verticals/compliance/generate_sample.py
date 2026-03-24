"""Generate a deterministic compliance/audit sample .chronicle file."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_compliance.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "compliance.json"

EVIDENCE_1 = (
    "Finance ledger export states invoice INV-204 was recognized as revenue on 2024-03-31 "
    "under quarter-close adjustments."
)
EVIDENCE_2 = (
    "Customer delivery receipt for INV-204 is signed on 2024-04-02, "
    "indicating fulfillment in the following period."
)
EVIDENCE_3 = (
    "Internal audit memo: revenue timing for INV-204 is disputed and requires exception tracking "
    "until policy interpretation is approved."
)


def _span_for_quote(text: str, quote: str) -> dict[str, int]:
    start = text.index(quote)
    end = start + len(quote)
    return {"start_char": start, "end_char": end}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic compliance sample .chronicle."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output .chronicle path (default: frontend/public/sample_compliance.chronicle)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    args = _parse_args(argv)
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_compliance_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation("Compliance sample: revenue timing exception")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            _, ev1_uid = session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            _, ev2_uid = session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            _, ev3_uid = session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            _, src1_uid = session.register_source(
                inv_uid,
                "General ledger export",
                "organization",
                independence_notes="Accounting system output independent of customer delivery logs.",
                reliability_notes="System-generated artifact with posting metadata.",
                workspace="forge",
            )
            _, src2_uid = session.register_source(
                inv_uid,
                "Signed delivery receipt",
                "document",
                independence_notes="Operational fulfillment record independent from ledger adjustments.",
                reliability_notes="Signed document with explicit date stamp.",
                workspace="forge",
            )
            _, src3_uid = session.register_source(
                inv_uid,
                "Internal audit exception memo",
                "organization",
                independence_notes="Governance review layer independent of transaction posting systems.",
                reliability_notes="Internal policy interpretation note; action-oriented rather than dispositive.",
                workspace="forge",
            )
            session.link_evidence_to_source(
                ev1_uid, src1_uid, relationship="provided_by", workspace="forge"
            )
            session.link_evidence_to_source(
                ev2_uid, src2_uid, relationship="provided_by", workspace="forge"
            )
            session.link_evidence_to_source(
                ev3_uid, src3_uid, relationship="authored_by", workspace="forge"
            )

            _, claim_a_uid = session.propose_claim(
                inv_uid, "INV-204 revenue was properly recognized in March 2024."
            )
            _, claim_b_uid = session.propose_claim(
                inv_uid, "INV-204 revenue should be recognized in April 2024."
            )
            _, claim_c_uid = session.propose_claim(
                inv_uid, "Revenue timing for INV-204 requires a tracked compliance exception."
            )
            session.type_claim(
                claim_a_uid,
                "SAC",
                rationale="Ledger artifact supports claim but is contested by delivery timing evidence.",
                workspace="forge",
            )
            session.type_claim(
                claim_b_uid,
                "SAC",
                rationale="Delivery evidence supports later recognition but conflicts with ledger posting.",
                workspace="forge",
            )
            session.type_claim(
                claim_c_uid,
                "INFERENCE",
                rationale="Compliance posture inferred from conflicting transactional artifacts.",
                workspace="forge",
            )
            session.temporalize_claim(
                claim_b_uid,
                {
                    "known_range_start": "2024-04-01T00:00:00Z",
                    "known_range_end": "2024-04-30T23:59:59Z",
                    "temporal_confidence": 0.8,
                    "time_notes": "Receipt indicates early-April fulfillment date.",
                },
                workspace="forge",
            )

            quote_a = "recognized as revenue on 2024-03-31"
            quote_b = "delivery receipt for INV-204 is signed on 2024-04-02"
            quote_c = "revenue timing for INV-204 is disputed and requires exception tracking"

            _, span_a_uid = session.anchor_span(
                inv_uid, ev1_uid, "text_offset", _span_for_quote(EVIDENCE_1, quote_a), quote=quote_a
            )
            _, span_b_uid = session.anchor_span(
                inv_uid, ev2_uid, "text_offset", _span_for_quote(EVIDENCE_2, quote_b), quote=quote_b
            )
            _, span_c_uid = session.anchor_span(
                inv_uid, ev3_uid, "text_offset", _span_for_quote(EVIDENCE_3, quote_c), quote=quote_c
            )
            session.link_support(
                inv_uid,
                span_a_uid,
                claim_a_uid,
                rationale="Ledger posting date supports March recognition position.",
            )
            session.link_support(
                inv_uid,
                span_b_uid,
                claim_b_uid,
                rationale="Signed delivery timing supports April recognition interpretation.",
            )
            session.link_support(
                inv_uid,
                span_c_uid,
                claim_c_uid,
                rationale="Audit memo requires tracked exception workflow while conflict remains open.",
            )
            session.link_challenge(
                inv_uid,
                span_b_uid,
                claim_a_uid,
                rationale="Post-quarter fulfillment timing challenges March recognition certainty.",
                workspace="forge",
            )
            session.link_challenge(
                inv_uid,
                span_a_uid,
                claim_b_uid,
                rationale="Ledger close adjustment challenges April-only interpretation.",
                workspace="forge",
            )

            session.declare_tension(
                inv_uid,
                claim_a_uid,
                claim_b_uid,
                tension_kind="contradiction",
                notes="Revenue timing conflict between ledger posting and delivery evidence.",
                workspace="forge",
            )

            out = tmp_path / "sample_compliance.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
