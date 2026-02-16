"""
Generate vertical-tagged seed corpora: 50 journalism + 50 legal synthetic investigations (M6).

Each output is a .chronicle file. Vertical tagging is by output directory (journalism/ vs legal/).
For fine-tuning or evaluation on vertical-specific data. CC-BY 4.0. See docs/benchmark/vertical_corpora/README.md.

Run from repo root:
  PYTHONPATH=. python3 scripts/benchmark_data/generate_vertical_corpora.py

Optional:
  --journalism N   number of journalism investigations (default 50)
  --legal N        number of legal investigations (default 50)
  --output DIR     output base dir (default docs/benchmark/vertical_corpora)
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "benchmark" / "vertical_corpora"
PROFILE_SOURCE = REPO_ROOT / "docs" / "spec" / "profiles" / "policy_investigative_journalism.json"


def _j_date(run: int) -> str:
    """Vary date for journalism (2024-01-01 + run days)."""
    from datetime import datetime, timedelta
    d = datetime(2024, 1, 1) + timedelta(days=run)
    return d.strftime("%Y-%m-%d")


def _j_id(run: int) -> str:
    """Short id for variety."""
    return f"R{100 + run}"


# ---- Journalism builders (one claim, two supports; parameterized by run 0..N-1) ----

def journalism_board_decision(session, inv_uid: str, run: int) -> None:
    """Board/council decision with two source lines."""
    d = _j_date(run)
    e1 = f"Meeting minutes ({d}): the board approved the budget. Vote was unanimous. Ref {_j_id(run)}."
    e2 = f"Treasurer memo: budget approval completed {d}. All signatories recorded."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, f"The board approved the budget on {d}.")
    for ev_uid, start, end in [(ev1, 20, 20 + len(f"the board approved the budget")), (ev2, 24, 24 + len(f"budget approval completed {d}"))]:
        _, span_uid = session.anchor_span(inv_uid, ev_uid, "text_offset", {"start_char": start, "end_char": end}, quote="")
        session.link_support(inv_uid, span_uid, c_uid)


def journalism_witness_sighting(session, inv_uid: str, run: int) -> None:
    """Single witness report (one support — weak)."""
    d = _j_date(run)
    e1 = f"Witness statement ({d}): the subject was seen at the venue at 14:00. Ref {_j_id(run)}."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev = evidence[0].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, f"The subject was at the venue on {d} at 14:00.")
    _, span_uid = session.anchor_span(inv_uid, ev, "text_offset", {"start_char": 28, "end_char": 28 + len("the subject was seen at the venue at 14:00")}, quote="")
    session.link_support(inv_uid, span_uid, c_uid)


def journalism_two_source_claim(session, inv_uid: str, run: int) -> None:
    """Two independent sources for a fact."""
    d = _j_date(run)
    e1 = f"Source A report: the event took place on {d}. Confirmed by desk."
    e2 = f"Source B report: event date {d}. Independent verification."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, f"The event took place on {d}.")
    _, s1 = session.anchor_span(inv_uid, ev1, "text_offset", {"start_char": 18, "end_char": 18 + len(f"the event took place on {d}")}, quote="")
    _, s2 = session.anchor_span(inv_uid, ev2, "text_offset", {"start_char": 15, "end_char": 15 + len(f"event date {d}")}, quote="")
    session.link_support(inv_uid, s1, c_uid)
    session.link_support(inv_uid, s2, c_uid)


def journalism_correction(session, inv_uid: str, run: int) -> None:
    """Initial figure then correction (resolved tension)."""
    d = _j_date(run)
    e1 = f"Initial release: attendance was 500. Dated {d}."
    e2 = f"Correction: attendance restated to 480 after recount. Dated {d}."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c1 = session.propose_claim(inv_uid, "Attendance was 500.")
    _, c2 = session.propose_claim(inv_uid, "Attendance was restated to 480.")
    _, s1 = session.anchor_span(inv_uid, ev1, "text_offset", {"start_char": 20, "end_char": 35}, quote="attendance was 500")
    _, s2 = session.anchor_span(inv_uid, ev2, "text_offset", {"start_char": 32, "end_char": 55}, quote="attendance restated to 480")
    session.link_support(inv_uid, s1, c1)
    session.link_support(inv_uid, s2, c2)
    _, t_uid = session.declare_tension(inv_uid, c1, c2, tension_kind="source_conflict_unadjudicated", workspace="forge")
    session.update_tension_status(t_uid, "RESOLVED", reason="Recount supersedes initial figure.", workspace="forge")


def journalism_three_sources(session, inv_uid: str, run: int) -> None:
    """Three sources (strong corroboration)."""
    d = _j_date(run)
    e1 = f"Witness 1: the announcement was made on {d} at 10:00."
    e2 = f"Witness 2: announcement on {d} at 10:00."
    e3 = f"Official log: announcement {d} 10:00. Ref {_j_id(run)}."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e3.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2, ev3 = evidence[0].evidence_uid, evidence[1].evidence_uid, evidence[2].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, f"The announcement was made on {d} at 10:00.")
    q1 = "the announcement was made on " + d + " at 10:00"
    q2 = "announcement on " + d + " at 10:00"
    q3 = "announcement " + d + " 10:00"
    for ev_uid, start, end in [(ev1, 11, 11 + len(q1)), (ev2, 14, 14 + len(q2)), (ev3, 18, 18 + len(q3))]:
        _, span_uid = session.anchor_span(inv_uid, ev_uid, "text_offset", {"start_char": start, "end_char": end}, quote="")
        session.link_support(inv_uid, span_uid, c_uid)


JOURNALISM_BUILDERS: list[Callable[..., None]] = [
    journalism_board_decision,
    journalism_witness_sighting,
    journalism_two_source_claim,
    journalism_correction,
    journalism_three_sources,
]


# ---- Legal builders ----

def _l_date(run: int) -> str:
    from datetime import datetime, timedelta
    return (datetime(2024, 2, 1) + timedelta(days=run)).strftime("%Y-%m-%d")


def legal_contract_clause(session, inv_uid: str, run: int) -> None:
    """Single clause with two exhibit refs."""
    d = _l_date(run)
    e1 = f"Contract Section 3.{run + 1}: Payment is due within 30 days of delivery. Effective {d}."
    e2 = f"Amendment: payment terms 30 days from delivery. Dated {d}."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "Payment is due within 30 days of delivery.")
    _, s1 = session.anchor_span(inv_uid, ev1, "text_offset", {"start_char": 22, "end_char": 22 + len("Payment is due within 30 days of delivery")}, quote="")
    _, s2 = session.anchor_span(inv_uid, ev2, "text_offset", {"start_char": 18, "end_char": 18 + len("payment terms 30 days from delivery")}, quote="")
    session.link_support(inv_uid, s1, c_uid)
    session.link_support(inv_uid, s2, c_uid)


def legal_deposition_excerpt(session, inv_uid: str, run: int) -> None:
    """Single source (deposition)."""
    d = _l_date(run)
    e1 = f"Deposition excerpt ({d}): The witness stated that the meeting occurred as recorded. Ref Ex-{100 + run}."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev = evidence[0].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "The meeting occurred as recorded.")
    _, span_uid = session.anchor_span(inv_uid, ev, "text_offset", {"start_char": 35, "end_char": 35 + len("the meeting occurred as recorded")}, quote="")
    session.link_support(inv_uid, span_uid, c_uid)


def legal_notification_assertion(session, inv_uid: str, run: int) -> None:
    """Two docs supporting notification fact."""
    d = _l_date(run)
    e1 = f"Letter dated {d}: Notice was sent to the counterparty on that date. Ref N-{run}."
    e2 = f"Delivery log: notification sent {d}. Confirmed."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, f"Notice was sent to the counterparty on {d}.")
    _, s1 = session.anchor_span(inv_uid, ev1, "text_offset", {"start_char": 15, "end_char": 15 + len(f"Notice was sent to the counterparty on {d}")}, quote="")
    _, s2 = session.anchor_span(inv_uid, ev2, "text_offset", {"start_char": 22, "end_char": 22 + len(f"notification sent {d}")}, quote="")
    session.link_support(inv_uid, s1, c_uid)
    session.link_support(inv_uid, s2, c_uid)


def legal_dispute_resolved(session, inv_uid: str, run: int) -> None:
    """Two positions, tension resolved."""
    d = _l_date(run)
    e1 = f"Party A: The obligation was fulfilled on {d}. Exhibit A-{run}."
    e2 = f"Settlement: Parties agree obligation was fulfilled as of {d}. No further claim."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2 = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c1 = session.propose_claim(inv_uid, f"The obligation was fulfilled on {d}.")
    _, c2 = session.propose_claim(inv_uid, "Parties agree the obligation was fulfilled; no further claim.")
    _, s1 = session.anchor_span(inv_uid, ev1, "text_offset", {"start_char": 14, "end_char": 14 + len(f"The obligation was fulfilled on {d}")}, quote="")
    _, s2 = session.anchor_span(inv_uid, ev2, "text_offset", {"start_char": 28, "end_char": 28 + len("obligation was fulfilled")}, quote="")
    session.link_support(inv_uid, s1, c1)
    session.link_support(inv_uid, s2, c2)
    _, t_uid = session.declare_tension(inv_uid, c1, c2, tension_kind="source_conflict_unadjudicated", workspace="forge")
    session.update_tension_status(t_uid, "RESOLVED", reason="Settlement agreement.", workspace="forge")


def legal_three_exhibits(session, inv_uid: str, run: int) -> None:
    """Three exhibits (strong)."""
    d = _l_date(run)
    e1 = f"Exhibit {run}.1: The amount was $10,000. Dated {d}."
    e2 = f"Exhibit {run}.2: Amount $10,000. Verified."
    e3 = f"Exhibit {run}.3: Payment of $10,000 on {d}. Ref ledger."
    session.ingest_evidence(inv_uid, e1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e2.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, e3.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1, ev2, ev3 = evidence[0].evidence_uid, evidence[1].evidence_uid, evidence[2].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "The amount was $10,000.")
    # e1 "Exhibit N.1: The amount..." start 12; e2 "Exhibit N.2: Amount..." start 12; e3 "Exhibit N.3: Payment of $10,000..." start at "Payment of "
    off1 = len(f"Exhibit {run}.1: ")
    off2 = len(f"Exhibit {run}.2: ")
    off3 = len(f"Exhibit {run}.3: ") + len("Payment of ")
    for ev_uid, start, end in [(ev1, off1, off1 + len("The amount was $10,000")), (ev2, off2, off2 + len("Amount $10,000")), (ev3, off3, off3 + len("$10,000"))]:
        _, span_uid = session.anchor_span(inv_uid, ev_uid, "text_offset", {"start_char": start, "end_char": end}, quote="")
        session.link_support(inv_uid, span_uid, c_uid)


LEGAL_BUILDERS: list[Callable[..., None]] = [
    legal_contract_clause,
    legal_deposition_excerpt,
    legal_notification_assertion,
    legal_dispute_resolved,
    legal_three_exhibits,
]


def main() -> int:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    parser = argparse.ArgumentParser(description="Generate vertical-tagged seed corpora (journalism + legal).")
    parser.add_argument("--journalism", type=int, default=50, help="Number of journalism investigations")
    parser.add_argument("--legal", type=int, default=50, help="Number of legal investigations")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output base directory")
    args = parser.parse_args()

    out_base = Path(args.output).resolve()
    j_dir = out_base / "journalism"
    l_dir = out_base / "legal"
    j_dir.mkdir(parents=True, exist_ok=True)
    l_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chronicle_vertical_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)

        with ChronicleSession(tmp_path) as session:
            # Journalism
            for i in range(args.journalism):
                title = f"Journalism seed {i + 1}"
                session.create_investigation(title)
                invs = session.read_model.list_investigations()
                inv_uid = invs[-1].investigation_uid
                builder = JOURNALISM_BUILDERS[i % len(JOURNALISM_BUILDERS)]
                builder(session, inv_uid, i % 10)
                out_name = f"journalism_{i + 1:03d}.chronicle"
                session.export_investigation(inv_uid, tmp_path / out_name)
                (j_dir / out_name).write_bytes((tmp_path / out_name).read_bytes())

            # Legal (new project state: we have args.journalism invs already; create_investigation adds more)
            for i in range(args.legal):
                title = f"Legal seed {i + 1}"
                session.create_investigation(title)
                invs = session.read_model.list_investigations()
                inv_uid = invs[-1].investigation_uid
                builder = LEGAL_BUILDERS[i % len(LEGAL_BUILDERS)]
                builder(session, inv_uid, i % 10)
                out_name = f"legal_{i + 1:03d}.chronicle"
                session.export_investigation(inv_uid, tmp_path / out_name)
                (l_dir / out_name).write_bytes((tmp_path / out_name).read_bytes())

    print(f"Written {args.journalism} journalism to {j_dir}")
    print(f"Written {args.legal} legal to {l_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
