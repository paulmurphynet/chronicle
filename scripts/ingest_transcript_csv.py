"""
Ingest a transcript CSV into Chronicle: one row = one evidence item + one span + one claim (statement as claim).

Use this for inquests, hearings, interviews: each line becomes evidence and an attributable claim
so you can export to .chronicle and push to the Aura graph. Optional: speaker column → actor_id.

For attribution: set CHRONICLE_ACTOR_ID (and optionally CHRONICLE_ACTOR_TYPE) so the investigation
creation and run are attributed to the curator, e.g. CHRONICLE_ACTOR_ID=jane_doe.

Run from repo root:
  PYTHONPATH=. python scripts/ingest_transcript_csv.py transcript.csv --text-col "text" --out lizzie_borden.chronicle
  CHRONICLE_ACTOR_ID=jane_doe PYTHONPATH=. python scripts/ingest_transcript_csv.py transcript.csv --text-col "statement" --speaker-col "speaker" --title "Lizzie Borden inquest" --out lizzie_borden.chronicle

Then ingest into your graph:
  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py lizzie_borden.chronicle

See docs/ingesting-transcripts.md for design and optional tools (factual extraction, tension detection).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a transcript CSV into Chronicle (one row = one evidence + one claim)."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the transcript CSV")
    parser.add_argument(
        "--text-col",
        default="text",
        help="CSV column containing the statement text (default: text)",
    )
    parser.add_argument(
        "--speaker-col",
        default="",
        help="Optional CSV column for speaker name (used as actor_id)",
    )
    parser.add_argument(
        "--title",
        default="Transcript",
        help="Investigation title (default: Transcript)",
    )
    parser.add_argument(
        "--out",
        default="transcript.chronicle",
        help="Output .chronicle path (default: transcript.chronicle)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV file encoding (default: utf-8)",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV delimiter (default: ,). Use '\\t' for tab.",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        default=True,
        help="Skip rows with empty text (default: True)",
    )
    parser.add_argument(
        "--no-skip-empty",
        action="store_false",
        dest="skip_empty",
        help="Do not skip rows with empty text",
    )
    args = parser.parse_args()

    csv_path = args.csv_path.resolve()
    if not csv_path.is_file():
        print(f"Error: not a file: {csv_path}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    if out_path.suffix != ".chronicle":
        out_path = out_path.with_suffix(".chronicle")

    delimiter = args.delimiter.replace("\\t", "\t")
    try:
        with open(csv_path, encoding=args.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                print("Error: CSV has no header row", file=sys.stderr)
                return 1
            if args.text_col not in reader.fieldnames:
                print(
                    f"Error: column '{args.text_col}' not in CSV. Columns: {list(reader.fieldnames)}",
                    file=sys.stderr,
                )
                return 1
            rows = list(reader)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Error: no data rows", file=sys.stderr)
        return 1

    speaker_col = args.speaker_col.strip() or None
    if speaker_col and reader.fieldnames and speaker_col not in reader.fieldnames:
        print(f"Warning: speaker column '{speaker_col}' not in CSV; ignoring", file=sys.stderr)
        speaker_col = None

    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    with tempfile.TemporaryDirectory(prefix="chronicle_transcript_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        with ChronicleSession(tmp_path) as session:
            curator_id = os.environ.get("CHRONICLE_ACTOR_ID") or "default"
            curator_type = os.environ.get("CHRONICLE_ACTOR_TYPE") or "human"
            session.create_investigation(
                args.title,
                actor_id=curator_id,
                actor_type=curator_type,
            )
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            for i, row in enumerate(rows):
                text = (row.get(args.text_col) or "").strip()
                if args.skip_empty and not text:
                    continue
                speaker = (row.get(speaker_col) or "").strip() if speaker_col else ""
                actor_id = speaker or "unknown"

                event_id, evidence_uid = session.ingest_evidence(
                    inv_uid,
                    text.encode("utf-8"),
                    "text/plain",
                    original_filename=f"row_{i + 1}",
                    actor_id=actor_id,
                    actor_type="human",
                )
                length = len(text)
                _, span_uid = session.anchor_span(
                    inv_uid,
                    evidence_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": length},
                    quote=text[:300] + ("..." if len(text) > 300 else ""),
                )
                claim_text = f"{speaker}: {text}" if speaker else text
                _, claim_uid = session.propose_claim(
                    inv_uid,
                    claim_text,
                    actor_id=actor_id,
                    actor_type="human",
                )
                session.link_support(inv_uid, span_uid, claim_uid)

            session.export_investigation(inv_uid, tmp_path / "export.chronicle")

        out_path.write_bytes((tmp_path / "export.chronicle").read_bytes())

    print(f"Ingested {len(rows)} rows into investigation '{args.title}'.")
    print(f"Exported: {out_path}")
    print(f"Next: PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
