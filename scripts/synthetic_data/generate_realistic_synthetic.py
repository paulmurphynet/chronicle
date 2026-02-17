"""
Generate realistic synthetic .chronicle files for testing the Aura graph pipeline.

Creates 10 investigations across different "real life" scenarios: revenue, outages,
due diligence, product launch, RAG-style Q&A, compliance, support tickets. Outputs
one .chronicle per investigation so you can ingest them into your graph project.

Run from repo root:
  PYTHONPATH=. python scripts/synthetic_data/generate_realistic_synthetic.py
  PYTHONPATH=. python scripts/synthetic_data/generate_realistic_synthetic.py --ingest   # then ingest all into graph

Output dir: scripts/synthetic_data/output/ (created if missing).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


# ---------- Scenario 1: Strong — Acme Corp Q3 revenue (three sources) ----------
TITLE_1 = "Acme Corp Q3 2024 revenue"
E1_A = "Acme Corp earnings release, Oct 2024: Q3 revenue was $12.4M, up 8% YoY. GAAP."
E1_B = "CFO memo to board: Q3 revenue $12.4M as reported. Audit committee notified."
E1_C = "Independent audit excerpt: Revenue recognition for Q3 2024 totals $12.4M."


def make_acme_revenue(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E1_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E1_B.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E1_C.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    e1, e2, e3 = evidence[0].evidence_uid, evidence[1].evidence_uid, evidence[2].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "Acme Corp Q3 2024 revenue was $12.4M.")
    for ev_uid, start, end in [(e1, 45, 63), (e2, 28, 46), (e3, 58, 76)]:
        _, span_uid = session.anchor_span(
            inv_uid, ev_uid, "text_offset", {"start_char": start, "end_char": end}, quote="Q3 revenue was $12.4M"
        )
        session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 2: Challenged — Nexus API outage ----------
TITLE_2 = "Nexus API outage resolution time"
E2_SUP = "Status page update 2024-10-15: Nexus API outage resolved at 14:00 UTC. Services restored."
E2_CH = "Incident log 2024-10-15: Full recovery confirmed 14:32 UTC. Post-mortem scheduled."


def make_nexus_outage(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E2_SUP.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E2_CH.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "Nexus API outage was resolved by 14:00 UTC on 2024-10-15.")
    _, span_sup = session.anchor_span(
        inv_uid, evidence[0].evidence_uid, "text_offset",
        {"start_char": 45, "end_char": 78}, quote="outage resolved at 14:00 UTC",
    )
    _, span_ch = session.anchor_span(
        inv_uid, evidence[1].evidence_uid, "text_offset",
        {"start_char": 42, "end_char": 65}, quote="Full recovery confirmed 14:32 UTC",
    )
    session.link_support(inv_uid, span_sup, c_uid)
    session.link_challenge(inv_uid, span_ch, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 3: Resolved tension — Meridian merger numbers ----------
TITLE_3 = "Meridian merger target revenue"
E3_A = "Deal memo: Meridian target FY2024 revenue $50M. Pre-adjustment figure."
E3_B = "Adjusted DD report: Post-adjustment target revenue $48M. Signed 2024-09-01."


def make_meridian_merger(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E3_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E3_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c1 = session.propose_claim(inv_uid, "Meridian target revenue was $50M.")
    _, c2 = session.propose_claim(inv_uid, "Meridian target revenue was $48M after adjustments.")
    _, s1 = session.anchor_span(inv_uid, evidence[0].evidence_uid, "text_offset", {"start_char": 28, "end_char": 52}, quote="target FY2024 revenue $50M")
    _, s2 = session.anchor_span(inv_uid, evidence[1].evidence_uid, "text_offset", {"start_char": 38, "end_char": 62}, quote="target revenue $48M")
    session.link_support(inv_uid, s1, c1)
    session.link_support(inv_uid, s2, c2)
    _, t_uid = session.declare_tension(inv_uid, c1, c2, tension_kind="source_conflict_unadjudicated", workspace="forge")
    session.update_tension_status(t_uid, "RESOLVED", reason="Adjusted DD supersedes; $48M is the closing figure.", workspace="forge")
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 4: Weak — Product Z launch (single source) ----------
TITLE_4 = "Product Z launch regions"
E4 = "Internal GTM slide 2024-11: Product Z launch in US and EU in Q1 2025. No external confirmation yet."


def make_product_z_launch(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E4.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "Product Z will launch in US and EU in Q1 2025.")
    _, span_uid = session.anchor_span(
        inv_uid, evidence[0].evidence_uid, "text_offset",
        {"start_char": 38, "end_char": 72}, quote="Product Z launch in US and EU in Q1 2025",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 5: Support ticket — refund timing (support + challenge) ----------
TITLE_5 = "Customer escalation 8841 refund timing"
E5_SUP = "Ticket 8841 resolution note: Refund processed 2024-10-10. Customer notified. 5 business days from request."
E5_CH = "Customer email 2024-10-12: Still no refund. Request was 2024-10-01. Escalating."


def make_escalation_8841(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E5_SUP.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E5_CH.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "Refund for escalation 8841 was issued within 5 business days.")
    _, span_sup = session.anchor_span(
        inv_uid, evidence[0].evidence_uid, "text_offset",
        {"start_char": 28, "end_char": 75}, quote="Refund processed 2024-10-10. Customer notified. 5 business days",
    )
    _, span_ch = session.anchor_span(
        inv_uid, evidence[1].evidence_uid, "text_offset",
        {"start_char": 25, "end_char": 52}, quote="Still no refund. Request was 2024-10-01",
    )
    session.link_support(inv_uid, span_sup, c_uid)
    session.link_challenge(inv_uid, span_ch, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 6: RAG-style — company founding date (strong) ----------
TITLE_6 = "RAG eval: company founding date"
E6_A = "About us: TechFlow Inc was founded in 1987 in Boston. Originally a hardware supplier."
E6_B = "Investor relations: TechFlow, established 1987, went public in 1999."


def make_rag_founding(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E6_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E6_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "TechFlow Inc was founded in 1987.")
    for ev, start, end in [(evidence[0], 22, 42), (evidence[1], 28, 48)]:
        _, span_uid = session.anchor_span(
            inv_uid, ev.evidence_uid, "text_offset", {"start_char": start, "end_char": end}, quote="founded in 1987"
        )
        session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 7: Compliance control (resolved tension) ----------
TITLE_7 = "Compliance control 7.2 effectiveness"
E7_A = "Internal audit Q2 2024: Control 7.2 effective as of 2024-06-30. No exceptions."
E7_B = "Exception log: Control 7.2 had exception until 2024-07-15. Remediated and re-tested."


def make_compliance_72(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E7_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E7_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c1 = session.propose_claim(inv_uid, "Control 7.2 was effective as of end of Q2 2024.")
    _, c2 = session.propose_claim(inv_uid, "Control 7.2 had an exception until July 2024.")
    _, s1 = session.anchor_span(inv_uid, evidence[0].evidence_uid, "text_offset", {"start_char": 28, "end_char": 62}, quote="Control 7.2 effective as of 2024-06-30")
    _, s2 = session.anchor_span(inv_uid, evidence[1].evidence_uid, "text_offset", {"start_char": 22, "end_char": 58}, quote="Control 7.2 had exception until 2024-07-15")
    session.link_support(inv_uid, s1, c1)
    session.link_support(inv_uid, s2, c2)
    _, t_uid = session.declare_tension(inv_uid, c1, c2, tension_kind="source_conflict_unadjudicated", workspace="forge")
    session.update_tension_status(t_uid, "RESOLVED", reason="Exception log is authoritative; control effective from 2024-07-15.", workspace="forge")
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 8: Competitor pricing (two sources, strong) ----------
TITLE_8 = "Competitor pricing leak review"
E8_A = "Internal memo (confidential): Vendor X list price for Enterprise tier is $499/user/month. Source: sales call."
E8_B = "Redacted slide from Vendor X partner deck: Enterprise tier $499/user/mo. Dated 2024-09."


def make_competitor_pricing(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E8_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E8_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "Vendor X Enterprise tier list price is $499 per user per month.")
    _, s1 = session.anchor_span(inv_uid, evidence[0].evidence_uid, "text_offset", {"start_char": 52, "end_char": 88}, quote="Enterprise tier is $499/user/month")
    _, s2 = session.anchor_span(inv_uid, evidence[1].evidence_uid, "text_offset", {"start_char": 48, "end_char": 72}, quote="Enterprise tier $499/user/mo")
    session.link_support(inv_uid, s1, c_uid)
    session.link_support(inv_uid, s2, c_uid)
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 9: Open tension — two conflicting witness statements ----------
TITLE_9 = "Witness statements: meeting location"
E9_A = "Witness 1 statement: The handoff meeting was in Building A, room 301. I was there."
E9_B = "Witness 2 statement: The handoff was in Building B, lobby. I did not go to Building A."


def make_witness_conflict(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E9_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, E9_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c1 = session.propose_claim(inv_uid, "The handoff meeting was in Building A, room 301.")
    _, c2 = session.propose_claim(inv_uid, "The handoff meeting was in Building B, lobby.")
    _, s1 = session.anchor_span(inv_uid, evidence[0].evidence_uid, "text_offset", {"start_char": 32, "end_char": 62}, quote="handoff meeting was in Building A, room 301")
    _, s2 = session.anchor_span(inv_uid, evidence[1].evidence_uid, "text_offset", {"start_char": 28, "end_char": 54}, quote="handoff was in Building B, lobby")
    session.link_support(inv_uid, s1, c1)
    session.link_support(inv_uid, s2, c2)
    session.declare_tension(inv_uid, c1, c2, tension_kind="source_conflict_unadjudicated", workspace="forge")
    session.export_investigation(inv_uid, out_path)


# ---------- Scenario 10: RAG eval — weak single chunk ----------
TITLE_10 = "RAG eval: product availability"
E10 = "FAQ: Is Product Y available in the EU? Yes, as of 2024-08. Check your region for delivery dates."


def make_rag_availability(session, inv_uid: str, out_path: Path) -> None:
    session.ingest_evidence(inv_uid, E10.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    _, c_uid = session.propose_claim(inv_uid, "Product Y is available in the EU as of 2024-08.")
    _, span_uid = session.anchor_span(
        inv_uid, evidence[0].evidence_uid, "text_offset",
        {"start_char": 18, "end_char": 58}, quote="Yes, as of 2024-08. Check your region",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


SCENARIOS = [
    (TITLE_1, make_acme_revenue, "01_acme_q3_revenue.chronicle"),
    (TITLE_2, make_nexus_outage, "02_nexus_outage.chronicle"),
    (TITLE_3, make_meridian_merger, "03_meridian_merger.chronicle"),
    (TITLE_4, make_product_z_launch, "04_product_z_launch.chronicle"),
    (TITLE_5, make_escalation_8841, "05_escalation_8841.chronicle"),
    (TITLE_6, make_rag_founding, "06_rag_founding_date.chronicle"),
    (TITLE_7, make_compliance_72, "07_compliance_control_72.chronicle"),
    (TITLE_8, make_competitor_pricing, "08_competitor_pricing.chronicle"),
    (TITLE_9, make_witness_conflict, "09_witness_conflict.chronicle"),
    (TITLE_10, make_rag_availability, "10_rag_availability.chronicle"),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate realistic synthetic .chronicle files and optionally ingest into graph project."
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="After generating, ingest all .chronicle files into CHRONICLE_GRAPH_PROJECT and sync to Neo4j.",
    )
    args = parser.parse_args()

    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_synthetic_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        with ChronicleSession(tmp_path) as session:
            for i, (title, make_fn, out_name) in enumerate(SCENARIOS):
                session.create_investigation(title)
                invs = session.read_model.list_investigations()
                inv_uid = invs[i].investigation_uid
                make_fn(session, inv_uid, tmp_path / out_name)
        for _, _, out_name in SCENARIOS:
            shutil.copy2(tmp_path / out_name, OUTPUT_DIR / out_name)

    print(f"Generated {len(SCENARIOS)} .chronicle files in {OUTPUT_DIR}")
    for _, _, out_name in SCENARIOS:
        print(f"  {out_name}")

    if args.ingest:
        ingest_script = REPO_ROOT / "scripts" / "ingest_chronicle_to_aura.py"
        if not ingest_script.is_file():
            print("Ingest script not found; run ingest manually.", file=sys.stderr)
            return 0
        print("\nIngesting into graph project and syncing to Neo4j...")
        for _, _, out_name in SCENARIOS:
            path = OUTPUT_DIR / out_name
            rc = subprocess.call(
                [sys.executable, str(ingest_script), str(path)],
                cwd=str(REPO_ROOT),
                env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)},
            )
            if rc != 0:
                print(f"  Failed: {out_name}", file=sys.stderr)
            else:
                print(f"  Ingested: {out_name}")
        print("Done. Open Neo4j Browser to explore the graph.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
