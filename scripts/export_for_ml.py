"""
Export Chronicle project or .chronicle to training-friendly JSONL (M3).

Each line is one JSON object: claim_uid, claim_text, evidence_texts[], support_span_refs[],
defensibility_score (provenance_quality and optional full metrics). Use for SFT, preference
data, or evaluation. See docs/benchmark.md Section 2 and docs/technical-report.md.

Usage (from repo root):

  # From a project directory (has chronicle.db and evidence/)
  PYTHONPATH=. python3 scripts/export_for_ml.py --project /path/to/project --output claims_ml.jsonl

  # From a .chronicle file (imported to a temp dir, then exported)
  PYTHONPATH=. python3 scripts/export_for_ml.py --chronicle path/to/investigation.chronicle --output claims_ml.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _decode_evidence_content(blob: bytes, media_type: str) -> str | None:
    """Decode evidence bytes to text when possible; return None for non-text."""
    if not blob:
        return ""
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt.startswith("text/"):
        try:
            return blob.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None


def _span_ref(span_uid: str, evidence_uid: str, anchor_json: str) -> dict:
    """Build a support_span_ref entry (evidence_uid, span_uid, optional start/end)."""
    ref: dict = {"evidence_uid": evidence_uid, "span_uid": span_uid}
    try:
        anchor = json.loads(anchor_json) if anchor_json else {}
        if isinstance(anchor, dict):
            if "start_char" in anchor:
                ref["start_char"] = anchor["start_char"]
            if "end_char" in anchor:
                ref["end_char"] = anchor["end_char"]
    except Exception:
        pass
    return ref


def _export_from_session(session, output_path: Path | None, stdout: bool) -> int:
    """Iterate claims, build JSONL rows, write to file or stdout. Returns count of rows."""
    from chronicle.eval_metrics import defensibility_metrics_for_claim

    rm = session.read_model
    investigations = rm.list_investigations()
    count = 0

    def emit(obj: dict) -> None:
        nonlocal count
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        if stdout:
            sys.stdout.write(line)
        else:
            assert output_path is not None
            with output_path.open("a", encoding="utf-8") as f:
                f.write(line)
        count += 1

    for inv in investigations:
        claims = rm.list_claims_by_type(
            investigation_uid=inv.investigation_uid,
            include_withdrawn=False,
            limit=10_000,
        )
        for claim in claims:
            support_links = rm.get_support_for_claim(claim.claim_uid)
            evidence_texts: list[str] = []
            support_span_refs: list[dict] = []

            for link in support_links:
                span = rm.get_evidence_span(link.span_uid)
                if not span:
                    continue
                ev_item = rm.get_evidence_item(span.evidence_uid)
                if not ev_item:
                    continue
                support_span_refs.append(
                    _span_ref(span.span_uid, span.evidence_uid, span.anchor_json)
                )
                try:
                    blob = session.evidence.retrieve(ev_item.uri)
                except Exception:
                    blob = b""
                text = _decode_evidence_content(blob, ev_item.media_type)
                if text is not None:
                    # Optionally slice by span anchor (text_offset)
                    try:
                        anchor = json.loads(span.anchor_json) if span.anchor_json else {}
                        if (
                            isinstance(anchor, dict)
                            and "start_char" in anchor
                            and "end_char" in anchor
                        ):
                            s, e = anchor["start_char"], anchor["end_char"]
                            if isinstance(s, int) and isinstance(e, int):
                                text = text[s:e]
                    except Exception:
                        pass
                    evidence_texts.append(text)

            metrics = defensibility_metrics_for_claim(session, claim.claim_uid)
            defensibility_score = metrics.get("provenance_quality") if metrics else None
            defensibility_metrics = metrics  # full dict for optional use

            row = {
                "claim_uid": claim.claim_uid,
                "claim_text": claim.claim_text or "",
                "investigation_uid": claim.investigation_uid,
                "evidence_texts": evidence_texts,
                "support_span_refs": support_span_refs,
                "defensibility_score": defensibility_score,
            }
            if defensibility_metrics:
                row["defensibility_metrics"] = defensibility_metrics
            emit(row)

    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export Chronicle project or .chronicle to JSONL for ML (claim, evidence, defensibility)."
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Path to Chronicle project directory (contains chronicle.db)",
    )
    parser.add_argument(
        "--chronicle",
        type=Path,
        help="Path to a .chronicle file (will be imported to a temp dir for export)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSONL file path (default: stdout if --stdout)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write JSONL to stdout instead of a file",
    )
    args = parser.parse_args()

    if (args.project is None) == (args.chronicle is None):
        print("Exactly one of --project or --chronicle is required.", file=sys.stderr)
        return 1
    if not args.stdout and args.output is None:
        print("Either --output or --stdout is required.", file=sys.stderr)
        return 1
    if args.stdout and args.output is not None:
        print("Use either --output or --stdout, not both.", file=sys.stderr)
        return 1

    project_path: Path
    if args.chronicle:
        args.chronicle = args.chronicle.resolve()
        if not args.chronicle.is_file() or args.chronicle.suffix != ".chronicle":
            print(f"Not a .chronicle file: {args.chronicle}", file=sys.stderr)
            return 1
        import tempfile

        from chronicle.store.export_import import import_investigation

        with tempfile.TemporaryDirectory(prefix="chronicle_export_ml_") as tmp:
            project_path = Path(tmp)
            import_investigation(args.chronicle, project_path)
            from chronicle.store.session import ChronicleSession

            if args.output and not args.stdout:
                args.output.open("w", encoding="utf-8").close()  # truncate
            with ChronicleSession(project_path) as session:
                n = _export_from_session(
                    session,
                    args.output if not args.stdout else None,
                    stdout=args.stdout,
                )
    else:
        args.project = args.project.resolve()
        if not (args.project / "chronicle.db").is_file():
            print(f"Not a Chronicle project (no chronicle.db): {args.project}", file=sys.stderr)
            return 1
        from chronicle.store.session import ChronicleSession

        project_path = args.project
        if args.output and not args.stdout:
            args.output.open("w").close()
        with ChronicleSession(project_path) as session:
            n = _export_from_session(
                session,
                args.output if not args.stdout else None,
                stdout=args.stdout,
            )

    if not args.stdout:
        print(f"Wrote {n} claim row(s) to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
