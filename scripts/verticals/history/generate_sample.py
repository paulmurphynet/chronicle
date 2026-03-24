"""Generate a deterministic history/research sample .chronicle file."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample_history.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "policy-profiles" / "history_research.json"

EVIDENCE_1 = (
    "Archive letter dated 1865 states the bridge was completed in 1864 "
    "after final stonework inspection."
)
EVIDENCE_2 = (
    "Newspaper digest from 1863 reports the bridge opened in 1862 "
    "for limited traffic during unfinished works."
)
EVIDENCE_3 = (
    "Archivist synthesis note: completion year remains contested and should be framed "
    "as unresolved pending additional primary records."
)


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

            _, ev1_uid = session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            _, ev2_uid = session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            _, ev3_uid = session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")

            _, src1_uid = session.register_source(
                inv_uid,
                "Municipal archive letter (1865)",
                "document",
                independence_notes="Primary archive source independent from press summaries.",
                reliability_notes="Later-dated record with explicit completion language.",
                workspace="forge",
            )
            _, src2_uid = session.register_source(
                inv_uid,
                "Regional newspaper digest (1863)",
                "document",
                independence_notes="Separate publication workflow and observer network.",
                reliability_notes="Contemporaneous periodical summary with possible ambiguity.",
                workspace="forge",
            )
            _, src3_uid = session.register_source(
                inv_uid,
                "Archivist interpretation note",
                "organization",
                independence_notes="Modern synthesis separate from both primary historical records.",
                reliability_notes="Interpretive artifact; suitable for caveat framing, not as sole fact source.",
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

            _, claim_a_uid = session.propose_claim(inv_uid, "Bridge completion year was 1864.")
            _, claim_b_uid = session.propose_claim(inv_uid, "Bridge completion year was 1862.")
            _, claim_c_uid = session.propose_claim(
                inv_uid,
                "Completion year remains contested and should be presented with caveats.",
            )
            session.type_claim(
                claim_a_uid,
                "SAC",
                rationale="Single archival source supports claim; contradicted by contemporaneous digest.",
                workspace="forge",
            )
            session.type_claim(
                claim_b_uid,
                "SAC",
                rationale="Single periodical source supports claim; contradicted by archival letter.",
                workspace="forge",
            )
            session.type_claim(
                claim_c_uid,
                "INFERENCE",
                rationale="Historiographic caveat derived from conflicting records.",
                workspace="forge",
            )
            session.temporalize_claim(
                claim_a_uid,
                {
                    "known_range_start": "1864-01-01T00:00:00Z",
                    "known_range_end": "1864-12-31T23:59:59Z",
                    "temporal_confidence": 0.55,
                    "time_notes": "Completion phrasing may differ from opening/partial operation dates.",
                },
                workspace="forge",
            )

            quote_a = "bridge was completed in 1864"
            quote_b = "bridge opened in 1862"
            quote_c = "completion year remains contested and should be framed as unresolved"

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
                rationale="Archive letter explicitly states completion in 1864.",
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
                rationale="Periodical reports earlier opening date in 1862.",
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
                rationale="Archivist synthesis recommends unresolved framing.",
            )
            session.link_challenge(
                inv_uid,
                span_b_uid,
                claim_a_uid,
                rationale="Earlier opening report challenges strict 1864 completion interpretation.",
                workspace="forge",
            )
            session.link_challenge(
                inv_uid,
                span_a_uid,
                claim_b_uid,
                rationale="Archive letter challenges 1862-as-completion assertion.",
                workspace="forge",
            )

            session.declare_tension(
                inv_uid,
                claim_a_uid,
                claim_b_uid,
                tension_kind="contradiction",
                notes="Competing completion-year interpretations from distinct archival sources.",
                workspace="forge",
            )

            out = tmp_path / "sample_history.chronicle"
            session.export_investigation(inv_uid, out)

        output_path.write_bytes(out.read_bytes())

    print(f"Written {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
