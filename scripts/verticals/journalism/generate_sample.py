"""Generate deterministic journalism/OSINT sample .chronicle."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "journalism.json"

EVIDENCE_1 = (
    "Witness memo dated 2024-01-15 reports the subject was seen in London at 14:00. "
    "Observer notes include station timestamp and route details."
)
EVIDENCE_2 = (
    "Border-control travel record shows a booking to Paris on 2024-01-15 "
    "and no London entry for that date."
)
EVIDENCE_3 = (
    "Editorial desk review: conflicting accounts for 2024-01-15 location remain unresolved. "
    "Publish only with caveat language."
)


def _span_for_quote(text: str, quote: str) -> dict[str, int]:
    start = text.index(quote)
    end = start + len(quote)
    return {"start_char": start, "end_char": end}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic journalism sample .chronicle."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output .chronicle path (default: frontend/public/sample.chronicle)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    args = _parse_args(argv)
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_sample_journalism_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation("Journalism sample: contested location report")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            _, ev1_uid = session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            _, ev2_uid = session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            _, ev3_uid = session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            _, src1_uid = session.register_source(
                inv_uid,
                "Witness A memo",
                "person",
                independence_notes="Direct eyewitness account independent of transport records.",
                reliability_notes="Identity withheld in sample; statement is first-party but uncorroborated alone.",
                workspace="forge",
            )
            _, src2_uid = session.register_source(
                inv_uid,
                "Border-control log extract",
                "public_record",
                independence_notes="Administrative record produced by a separate institution.",
                reliability_notes="Structured record with timestamp metadata.",
                workspace="forge",
            )
            _, src3_uid = session.register_source(
                inv_uid,
                "Editorial desk synthesis note",
                "organization",
                independence_notes="Internal synthesis distinct from raw primary records.",
                reliability_notes="Second-order summary used for caveat decisions only.",
                workspace="forge",
            )
            session.link_evidence_to_source(
                ev1_uid, src1_uid, relationship="testified_to", workspace="forge"
            )
            session.link_evidence_to_source(
                ev2_uid, src2_uid, relationship="provided_by", workspace="forge"
            )
            session.link_evidence_to_source(
                ev3_uid, src3_uid, relationship="authored_by", workspace="forge"
            )

            _, c1_uid = session.propose_claim(
                inv_uid, "Subject was in London on 2024-01-15 at approximately 14:00."
            )
            _, c2_uid = session.propose_claim(inv_uid, "Subject was in Paris on 2024-01-15.")
            _, c3_uid = session.propose_claim(
                inv_uid, "Location remains unresolved and requires caveated reporting."
            )
            session.type_claim(
                c1_uid,
                "SAC",
                rationale="Single-source eyewitness statement; not established.",
                workspace="forge",
            )
            session.type_claim(
                c2_uid,
                "SAC",
                rationale="Single administrative travel record; conflicts with eyewitness account.",
                workspace="forge",
            )
            session.type_claim(
                c3_uid,
                "INFERENCE",
                rationale="Editorial synthesis from conflicting evidence.",
                workspace="forge",
            )
            session.temporalize_claim(
                c1_uid,
                {
                    "known_range_start": "2024-01-15T13:30:00Z",
                    "known_range_end": "2024-01-15T14:30:00Z",
                    "temporal_confidence": 0.6,
                    "time_notes": "Witness report timestamp is approximate.",
                },
                workspace="forge",
            )

            quote_1 = "subject was seen in London at 14:00"
            quote_2 = "booking to Paris on 2024-01-15"
            quote_3 = "conflicting accounts for 2024-01-15 location remain unresolved"

            _, span1_uid = session.anchor_span(
                inv_uid, ev1_uid, "text_offset", _span_for_quote(EVIDENCE_1, quote_1), quote=quote_1
            )
            _, span2_uid = session.anchor_span(
                inv_uid, ev2_uid, "text_offset", _span_for_quote(EVIDENCE_2, quote_2), quote=quote_2
            )
            _, span3_uid = session.anchor_span(
                inv_uid, ev3_uid, "text_offset", _span_for_quote(EVIDENCE_3, quote_3), quote=quote_3
            )

            session.link_support(
                inv_uid,
                span1_uid,
                c1_uid,
                rationale="Eyewitness statement provides direct support for London claim.",
            )
            session.link_support(
                inv_uid,
                span2_uid,
                c2_uid,
                rationale="Border-control record supports Paris travel claim for the same date.",
            )
            session.link_support(
                inv_uid,
                span3_uid,
                c3_uid,
                rationale="Editorial synthesis explicitly identifies unresolved conflict.",
            )
            session.link_challenge(
                inv_uid,
                span2_uid,
                c1_uid,
                rationale="Travel record conflicts with London-at-14:00 narrative.",
                workspace="forge",
            )
            session.link_challenge(
                inv_uid,
                span1_uid,
                c2_uid,
                rationale="Eyewitness account conflicts with same-day Paris interpretation.",
                workspace="forge",
            )

            session.declare_tension(
                inv_uid,
                c1_uid,
                c2_uid,
                tension_kind="contradiction",
                notes="Mutually inconsistent location claims for the same date.",
                workspace="forge",
            )

            out = tmp_path / "sample.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
