"""
Generate the Journalism/OSINT sample for "Try sample" (frontend/public/sample.chronicle).
Scenario: conflicting location reports (London vs Paris), claims, support links, one tension.
Deterministic so the file can be regenerated and verified in CI.
Run from repository root: PYTHONPATH=. python3 scripts/verticals/journalism/generate_sample.py
"""

import shutil
import tempfile
from pathlib import Path

# Script lives at scripts/verticals/journalism/generate_sample.py -> repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "frontend" / "public" / "sample.chronicle"
PROFILE_SOURCE = REPO_ROOT / "docs" / "spec" / "profiles" / "policy_investigative_journalism.json"

# Short evidence texts so we can anchor spans (start_char, end_char).
# Scenario is intentionally generic and fictional: anonymous subject, neutral locations, no real persons or events.
EVIDENCE_1 = (
    "Report dated 2024-01-15: the subject was seen in London at 14:00. "
    "Witness A confirmed the sighting."
)
EVIDENCE_2 = (
    "Travel records show a booking to Paris on 2024-01-15. "
    "No corresponding London entry for that date."
)
EVIDENCE_3 = (
    "Summary: conflicting accounts for 2024-01-15 location. "
    "London sighting vs Paris booking — resolve before publication."
)


def main() -> None:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chronicle_sample_journalism_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        # So the exported manifest records built_under_policy_id
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)
        with ChronicleSession(tmp_path) as session:
            session.create_investigation("OSINT sample")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
            session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")
            evidence = session.read_model.list_evidence_by_investigation(inv_uid)
            ev1_uid = evidence[0].evidence_uid
            ev2_uid = evidence[1].evidence_uid

            _, c1_uid = session.propose_claim(inv_uid, "Subject was in London on 2024-01-15.")
            _, c2_uid = session.propose_claim(inv_uid, "Subject was in Paris on 2024-01-15.")
            _, c3_uid = session.propose_claim(
                inv_uid, "Conflicting location reports must be resolved before publication."
            )

            # "the subject was seen in London" in EVIDENCE_1: start_char 28, end_char 58
            _, span1_uid = session.anchor_span(
                inv_uid,
                ev1_uid,
                "text_offset",
                {"start_char": 28, "end_char": 58},
                quote="the subject was seen in London",
            )
            session.link_support(inv_uid, span1_uid, c1_uid)

            # "booking to Paris on 2024-01-15" in EVIDENCE_2: start 24, end 52
            _, span2_uid = session.anchor_span(
                inv_uid,
                ev2_uid,
                "text_offset",
                {"start_char": 24, "end_char": 52},
                quote="booking to Paris on 2024-01-15",
            )
            session.link_support(inv_uid, span2_uid, c2_uid)

            session.declare_tension(inv_uid, c1_uid, c2_uid, workspace="forge")

            out = tmp_path / "sample.chronicle"
            session.export_investigation(inv_uid, out)
        OUTPUT_PATH.write_bytes(out.read_bytes())
    print(f"Written {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
