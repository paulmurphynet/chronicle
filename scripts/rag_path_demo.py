"""
Demonstrate the canonical Chronicle-backed RAG path: ingest evidence, optional extraction
(propose claim, link support), then query defensibility and reasoning trail.

Run from repository root:
  PYTHONPATH=. python3 scripts/rag_path_demo.py

No API server required; uses ChronicleSession (CLI-style). For the same flow via HTTP API,
see docs/INTEGRATING_WITH_CHRONICLE.md Section 8 "Canonical Chronicle-backed RAG path".
"""

import tempfile
from pathlib import Path


def main() -> None:
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    with tempfile.TemporaryDirectory(prefix="chronicle_rag_demo_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)

        with ChronicleSession(tmp_path) as session:
            # 1. Create investigation
            session.create_investigation("RAG path demo")
            inv_uid = session.read_model.list_investigations()[0].investigation_uid

            # 2. Ingest evidence
            text = b"The company reported revenue of $1.2M in Q1 2024."
            _, ev_uid = session.ingest_evidence(inv_uid, text, "text/plain")

            # 3. Optional extraction: propose claim and link support
            _, claim_uid = session.propose_claim(
                inv_uid, "Revenue in Q1 2024 was $1.2M."
            )
            _, span_uid = session.anchor_span(
                inv_uid,
                ev_uid,
                "text_offset",
                {"start_char": 0, "end_char": len(text.decode("utf-8"))},
                quote="The company reported revenue of $1.2M in Q1 2024.",
            )
            session.link_support(inv_uid, span_uid, claim_uid)

            # 4. Query defensibility
            scorecard = session.get_defensibility_score(claim_uid)
            print("Defensibility:", scorecard.provenance_quality if scorecard else "N/A")
            if scorecard:
                print("  Contradiction status:", scorecard.contradiction_status)
                print("  Corroboration:", scorecard.corroboration)

            # 5. Query reasoning trail
            trail = session.get_reasoning_trail_claim(claim_uid, limit=20)
            print("Reasoning trail events:", len(trail["events"]) if trail and trail.get("events") else 0)

            # Optional: reasoning brief (one artifact)
            brief = session.get_reasoning_brief(claim_uid, limit=20)
            if brief:
                print("Reasoning brief: claim + defensibility + trail assembled.")

    print("Done. See docs/integrating-with-chronicle.md Section 8 for full RAG path.")


if __name__ == "__main__":
    main()
