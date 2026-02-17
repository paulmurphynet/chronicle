"""
Add tensions to the Lizzie Borden inquest investigation from real conflicts in the transcript.

Conflicts identified from the CSV (where was Lizzie when her father came home; did she leave the house):
  1. Row 571: "I think in my room up stairs." vs Row 597: "I think, as nearly as I know, I think I was in the kitchen."
  2. Row 577: "I was on the stairs coming down when she let him in." vs Row 597: in the kitchen.
  3. Row 772: "No sir, I was in the kitchen." (when father let in) vs Row 577: on the stairs when Maggie let him in.
  4. Row 776: "I went in the sitting room long enough to direct some paper wrappers." (implies in house) vs Row 846: "I went out to the barn."

Run after ingesting the transcript into a Chronicle project. Uses the project that contains the
Lizzie Borden inquest (e.g. chronicle_graph_project if you ingested lizzie_borden.chronicle there).

  PYTHONPATH=. python scripts/add_lizzie_tensions.py --project chronicle_graph_project
  chronicle neo4j-sync --path chronicle_graph_project   # then re-sync to Aura
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "test_data" / "lb_inquest" / "inquest.csv"

# (row_id_a, row_id_b) - row id is the "id" column in the CSV (1-based in file, we match by id string)
TENSION_PAIRS = [
    ("571", "597"),   # upstairs vs kitchen when father came home
    ("577", "597"),   # on stairs when let him in vs in kitchen
    ("772", "577"),   # in kitchen when let in vs on stairs when let him in
    ("776", "846"),   # in sitting room (in house) vs went out to the barn
]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Add Lizzie Borden inquest tensions to an existing Chronicle project.")
    parser.add_argument("--project", default="chronicle_graph_project", help="Path to Chronicle project (default: chronicle_graph_project)")
    parser.add_argument("--investigation-uid", default="", help="Use this investigation UID instead of matching by title")
    parser.add_argument("--title", default="Lizzie Borden inquest", help="Investigation title to match (default: Lizzie Borden inquest)")
    parser.add_argument("--debug", action="store_true", help="Print sample claim texts from DB when lookups fail")
    args = parser.parse_args()

    project_path = Path(args.project)
    if not project_path.is_absolute():
        project_path = (REPO_ROOT / project_path).resolve()
    if not (project_path / "chronicle.db").is_file():
        print(f"Error: not a Chronicle project (no chronicle.db): {project_path}", file=sys.stderr)
        return 1

    if not CSV_PATH.is_file():
        print(f"Error: CSV not found: {CSV_PATH}", file=sys.stderr)
        return 1

    # Build row id -> (speaker, testimony) from CSV
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "id" not in reader.fieldnames or "speaker" not in reader.fieldnames or "testimony" not in reader.fieldnames:
            print("Error: CSV must have columns id, speaker, testimony", file=sys.stderr)
            return 1
        rows_by_id = {}
        for row in reader:
            row_id = (row.get("id") or "").strip()
            speaker = (row.get("speaker") or "").strip()
            testimony = (row.get("testimony") or "").strip()
            if row_id:
                rows_by_id[row_id] = (speaker, testimony)

    # Claim text format used by ingest_transcript_csv: "Speaker: testimony"
    def claim_text(speaker: str, testimony: str) -> str:
        return f"{speaker}: {testimony}" if speaker else testimony

    def normalize(t: str) -> str:
        """Collapse whitespace and strip so we can match despite small CSV/DB differences."""
        return " ".join((t or "").split())

    from chronicle.store.session import ChronicleSession

    with ChronicleSession(project_path) as session:
        investigations = session.read_model.list_investigations()
        inv = None
        if (args.investigation_uid or "").strip():
            for i in investigations:
                if i.investigation_uid == args.investigation_uid.strip():
                    inv = i
                    break
        else:
            title_match = (args.title or "Lizzie Borden inquest").strip()
            for i in investigations:
                t = (i.title or "").strip()
                if t == title_match or (title_match.lower() in t.lower() and "lizzie" in t.lower()):
                    inv = i
                    break
        if not inv:
            print("Error: no matching investigation in this project.", file=sys.stderr)
            print("Investigations in project:", file=sys.stderr)
            for i in investigations:
                print(f"  uid={i.investigation_uid}  title={i.title!r}", file=sys.stderr)
            print("Use --investigation-uid <uid> or --title '<exact title>' to specify which one.", file=sys.stderr)
            return 1
        inv_uid = inv.investigation_uid
        print(f"Using investigation: {inv.title!r} ({inv_uid})")

        claims = session.read_model.list_claims_by_type(investigation_uid=inv_uid, limit=10_000)
        text_to_uid = {c.claim_text: c.claim_uid for c in claims}
        normalized_to_uid = {normalize(c.claim_text): c.claim_uid for c in claims}

        def find_claim_uid(lookup: str) -> str | None:
            uid = text_to_uid.get(lookup) or normalized_to_uid.get(normalize(lookup))
            if uid:
                return uid
            lookup_n = normalize(lookup)
            for ct, c_uid in text_to_uid.items():
                if normalize(ct) == lookup_n:
                    return c_uid
            for c in claims:
                cn = normalize(c.claim_text)
                if cn == lookup_n:
                    return c.claim_uid
                if len(lookup_n) > 25 and lookup_n in cn:
                    return c.claim_uid
            return None

        if not text_to_uid:
            print("Error: no claims found for that investigation.", file=sys.stderr)
            return 1

        added = 0
        for id_a, id_b in TENSION_PAIRS:
            if id_a not in rows_by_id or id_b not in rows_by_id:
                print(f"Warning: row id {id_a} or {id_b} not in CSV; skipping pair.", file=sys.stderr)
                continue
            speaker_a, testimony_a = rows_by_id[id_a]
            speaker_b, testimony_b = rows_by_id[id_b]
            text_a = claim_text(speaker_a, testimony_a)
            text_b = claim_text(speaker_b, testimony_b)
            uid_a = find_claim_uid(text_a)
            uid_b = find_claim_uid(text_b)
            if not uid_a:
                print(f"Warning: claim not found for row {id_a}: {text_a[:60]}...", file=sys.stderr)
                if getattr(args, "debug", False):
                    for ct, uid in list(text_to_uid.items())[:3]:
                        print(f"  DB sample: {ct[:80]!r}...", file=sys.stderr)
                    for ct in list(text_to_uid.keys()):
                        if "up stairs" in ct or "kitchen" in ct:
                            print(f"  DB has: {ct[:90]!r}", file=sys.stderr)
                            break
                continue
            if not uid_b:
                print(f"Warning: claim not found for row {id_b}: {text_b[:60]}...", file=sys.stderr)
                continue
            session.declare_tension(
                inv_uid,
                uid_a,
                uid_b,
                tension_kind="source_conflict_unadjudicated",
                workspace="forge",
            )
            added += 1
            print(f"  Tension: row {id_a} vs row {id_b}")

    print(f"Added {added} tensions. Re-sync to Aura: chronicle neo4j-sync --path {project_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
