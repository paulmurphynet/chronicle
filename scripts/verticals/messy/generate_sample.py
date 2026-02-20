"""Generate deterministic messy-corpus stress sample .chronicle."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_messy.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "compliance.json"

EVIDENCE_1 = (
    "Draft operations email (timezone omitted) states board approval happened on 2024-04-28, "
    "pending final minutes review."
)
EVIDENCE_2 = (
    "Corrected board minutes issued 2024-05-03 state formal approval was recorded on 2024-05-01 "
    "after amendment language updates."
)
EVIDENCE_3 = (
    "Counsel memo references unresolved privilege issues around amendment chronology and includes "
    "redacted sections pending legal hold release."
)
EVIDENCE_4 = (
    "Archive ingestion log notes chronology sync lag; records indicate approval may have occurred "
    "between 2024-04-30 and 2024-05-02 depending on source timezone normalization."
)


def _span_for_quote(text: str, quote: str) -> dict[str, int]:
    start = text.index(quote)
    end = start + len(quote)
    return {"start_char": start, "end_char": end}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic messy corpus stress sample.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output .chronicle path (default: frontend/public/sample_messy.chronicle)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    args = _parse_args(argv)
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_messy_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation("Messy stress sample: supersession + redaction + ambiguity")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            _, ev1_uid = session.ingest_evidence(
                inv_uid,
                EVIDENCE_1.encode("utf-8"),
                "text/plain",
                metadata={"source_quality": "partial", "timezone": None},
            )
            _, ev2_uid = session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            _, ev3_uid = session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")
            _, ev4_uid = session.ingest_evidence(
                inv_uid,
                EVIDENCE_4.encode("utf-8"),
                "text/plain",
                metadata={"normalization_status": "pending"},
            )

            _, src1_uid = session.register_source(
                inv_uid,
                "Draft operations email export",
                "organization",
                independence_notes="Draft communication channel, independent from board minutes publication.",
                reliability_notes="Partial metadata and timezone omissions reduce certainty.",
                workspace="forge",
            )
            _, src2_uid = session.register_source(
                inv_uid,
                "Corrected board minutes",
                "public_record",
                independence_notes="Governance record independent from ad hoc operations messages.",
                reliability_notes="Formal correction issued after review.",
                workspace="forge",
            )
            _, src3_uid = session.register_source(
                inv_uid,
                "Counsel memo under legal hold",
                "organization",
                independence_notes="Legal analysis stream independent from operational chronology records.",
                reliability_notes="Contains redacted privileged sections.",
                workspace="forge",
            )
            session.link_evidence_to_source(ev1_uid, src1_uid, relationship="provided_by", workspace="forge")
            session.link_evidence_to_source(ev2_uid, src2_uid, relationship="provided_by", workspace="forge")
            session.link_evidence_to_source(ev3_uid, src3_uid, relationship="authored_by", workspace="forge")
            session.link_evidence_to_source(ev4_uid, src1_uid, relationship="provided_by", workspace="forge")

            session.supersede_evidence(
                ev2_uid,
                ev1_uid,
                "correction",
                reason="Corrected minutes supersede earlier draft chronology reference.",
                workspace="forge",
            )
            _, claim_a_uid = session.propose_claim(
                inv_uid, "Board amendment was formally approved on 2024-05-01."
            )
            _, claim_b_uid = session.propose_claim(
                inv_uid, "Amendment approval occurred in a late-April to early-May window."
            )
            _, claim_c_uid = session.propose_claim(
                inv_uid, "Chronology cannot be finalized without unredacted counsel context."
            )
            _, claim_d_uid = session.propose_claim(
                inv_uid, "Initial draft chronology was corrected by later governance records."
            )
            session.type_claim(
                claim_a_uid,
                "SAC",
                rationale="Corrected board minutes directly state the formal approval date.",
                workspace="forge",
            )
            session.type_claim(
                claim_b_uid,
                "SAC",
                rationale="Cross-source timezone and correction drift support a bounded window claim.",
                workspace="forge",
            )
            session.type_claim(
                claim_c_uid,
                "INFERENCE",
                rationale="Redacted counsel memo limits final certainty.",
                workspace="forge",
            )
            session.type_claim(
                claim_d_uid,
                "INFERENCE",
                rationale="Supersession lineage indicates a chronology correction event.",
                workspace="forge",
            )

            session.temporalize_claim(
                claim_a_uid,
                {
                    "known_as_of": "2024-05-03T00:00:00Z",
                    "known_range_start": "2024-05-01T00:00:00Z",
                    "known_range_end": "2024-05-01T23:59:59Z",
                    "temporal_confidence": 0.72,
                    "time_notes": "Corrected minutes pin approval to 2024-05-01.",
                },
                workspace="forge",
            )
            session.temporalize_claim(
                claim_b_uid,
                {
                    "known_as_of": "2024-05-03T00:00:00Z",
                    "known_range_start": "2024-04-30T00:00:00Z",
                    "known_range_end": "2024-05-02T23:59:59Z",
                    "temporal_confidence": 0.55,
                    "time_notes": "Timezone normalization and draft/correction drift widen the plausible window.",
                },
                workspace="forge",
            )

            quote_1 = "board approval happened on 2024-04-28"
            quote_2 = "formal approval was recorded on 2024-05-01"
            quote_3 = "includes redacted sections pending legal hold release"
            quote_4 = "approval may have occurred between 2024-04-30 and 2024-05-02"

            _, span1_uid = session.anchor_span(
                inv_uid, ev1_uid, "text_offset", _span_for_quote(EVIDENCE_1, quote_1), quote=quote_1
            )
            _, span2_uid = session.anchor_span(
                inv_uid, ev2_uid, "text_offset", _span_for_quote(EVIDENCE_2, quote_2), quote=quote_2
            )
            _, span3_uid = session.anchor_span(
                inv_uid, ev3_uid, "text_offset", _span_for_quote(EVIDENCE_3, quote_3), quote=quote_3
            )
            _, span4_uid = session.anchor_span(
                inv_uid, ev4_uid, "text_offset", _span_for_quote(EVIDENCE_4, quote_4), quote=quote_4
            )

            session.link_support(
                inv_uid,
                span2_uid,
                claim_a_uid,
                rationale="Corrected minutes support the formal 2024-05-01 date.",
            )
            session.link_support(
                inv_uid,
                span4_uid,
                claim_b_uid,
                rationale="Archive log supports a bounded uncertainty window.",
            )
            session.link_support(
                inv_uid,
                span3_uid,
                claim_c_uid,
                rationale="Redacted counsel content supports explicit caveating of chronology certainty.",
            )
            session.link_support(
                inv_uid,
                span2_uid,
                claim_d_uid,
                rationale="Later governance record evidences correction relative to the draft.",
            )
            session.link_challenge(
                inv_uid,
                span1_uid,
                claim_a_uid,
                rationale="Draft timeline challenges strict single-date confidence.",
                workspace="forge",
            )
            session.link_challenge(
                inv_uid,
                span2_uid,
                claim_b_uid,
                rationale="Formal date challenges broader uncertainty framing.",
                workspace="forge",
            )

            session.declare_tension(
                inv_uid,
                claim_a_uid,
                claim_b_uid,
                tension_kind="contradiction",
                notes="Single formal date conflicts with range-based interpretation.",
                workspace="forge",
            )

            out = tmp_path / "sample_messy.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
