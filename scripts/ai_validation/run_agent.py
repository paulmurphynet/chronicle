"""
Run the scenario validation driver for a scenario. Deterministic, rule-based
(no AI/LLM): creates project and investigation, ingests evidence, proposes
claims, links support, optionally declares tension, exports. No API server
required; uses ChronicleSession.

Run from repo root:
  PYTHONPATH=. python3 scripts/ai_validation/run_agent.py --scenario journalism_conflict

Output: writes export to scripts/ai_validation/out/<scenario_id>.chronicle and prints the path.

Phase 9 (optional): use --trace to write a run trace to reports/traces/<scenario_id>.json
for use with propose_learn_from_trace.py (suggest Learn guide annotations from successful runs).
"""

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = SCRIPT_DIR / "scenarios"
OUT_DIR = SCRIPT_DIR / "out"
REPORTS_DIR = SCRIPT_DIR / "reports"
TRACES_DIR = REPORTS_DIR / "traces"


def load_scenario(scenario_id: str) -> dict:
    """Load scenario JSON by id (e.g. journalism_conflict)."""
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Scenario not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _trace_append(
    trace: list[dict] | None, learn_step: int, action: str, count: int | None = None
) -> None:
    if trace is None:
        return
    entry: dict = {"learn_step": learn_step, "action": action}
    if count is not None:
        entry["count"] = count
    trace.append(entry)


def run_journalism_conflict(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute the London vs Paris conflict workflow from the scenario documents."""
    docs = scenario["documents"]
    if len(docs) < 2:
        raise ValueError("journalism_conflict scenario requires at least 2 documents")

    # Ingest evidence
    for doc in docs:
        content = doc["content"].encode("utf-8")
        session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", len(docs))

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid = evidence[0].evidence_uid
    ev2_uid = evidence[1].evidence_uid

    # Propose claims: two location claims + optional meta
    _, c1_uid = session.propose_claim(inv_uid, "Subject was in London on 2024-01-15.")
    _, c2_uid = session.propose_claim(inv_uid, "Subject was in Paris on 2024-01-15.")
    _trace_append(trace, 3, "propose_claims", 2)

    # Anchor spans and link support (London claim <- first doc, Paris claim <- second doc)
    _, span1_uid = session.anchor_span(
        inv_uid,
        ev1_uid,
        "text_offset",
        {"start_char": 28, "end_char": 58},
        quote="the subject was seen in London",
    )
    session.link_support(inv_uid, span1_uid, c1_uid)
    _, span2_uid = session.anchor_span(
        inv_uid,
        ev2_uid,
        "text_offset",
        {"start_char": 24, "end_char": 52},
        quote="booking to Paris on 2024-01-15",
    )
    session.link_support(inv_uid, span2_uid, c2_uid)
    _trace_append(trace, 3, "link_support", 2)

    # Declare tension between the two location claims
    session.declare_tension(inv_uid, c1_uid, c2_uid, workspace="forge")
    _trace_append(trace, 5, "declare_tension")


def run_legal_conflict(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute the conflicting delivery-date workflow from the scenario documents."""
    docs = scenario["documents"]
    if len(docs) < 2:
        raise ValueError("legal_conflict scenario requires at least 2 documents")

    # Ingest evidence
    for doc in docs:
        content = doc["content"].encode("utf-8")
        session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", len(docs))

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid = evidence[0].evidence_uid
    ev2_uid = evidence[1].evidence_uid

    # Propose claims: two delivery-date claims
    _, c1_uid = session.propose_claim(inv_uid, "Delivery due March 1, 2024.")
    _, c2_uid = session.propose_claim(inv_uid, "Delivery due April 15, 2024.")
    _trace_append(trace, 3, "propose_claims", 2)

    # Anchor spans and link support (claim 1 <- contract A, claim 2 <- contract B)
    # "deliver by March 1, 2024" in doc 1: start_char 37, end_char 61
    _, span1_uid = session.anchor_span(
        inv_uid,
        ev1_uid,
        "text_offset",
        {"start_char": 37, "end_char": 61},
        quote="deliver by March 1, 2024",
    )
    session.link_support(inv_uid, span1_uid, c1_uid)
    # "Delivery date is April 15, 2024" in doc 2: start_char 23, end_char 53
    _, span2_uid = session.anchor_span(
        inv_uid,
        ev2_uid,
        "text_offset",
        {"start_char": 23, "end_char": 53},
        quote="Delivery date is April 15, 2024",
    )
    session.link_support(inv_uid, span2_uid, c2_uid)
    _trace_append(trace, 3, "link_support", 2)

    # Declare tension between the two delivery-date claims
    session.declare_tension(inv_uid, c1_uid, c2_uid, workspace="forge")
    _trace_append(trace, 5, "declare_tension")


def run_journalism_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single-claim verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("journalism_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(
        inv_uid, "Company announced merger with Acme Corp, closing expected Q2 2024."
    )
    # "the merger with Acme Corp" in doc: start_char 54, end_char 79
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 54, "end_char": 79},
        quote="the merger with Acme Corp",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_legal_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single-clause verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("legal_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(inv_uid, "Payment terms are net 30 days from invoice date.")
    # "Payment terms are net 30 days from invoice date" in doc: start_char 20, end_char 67
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 20, "end_char": 67},
        quote="Payment terms are net 30 days from invoice date",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_compliance_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single control verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("compliance_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(inv_uid, "Access to PII must be logged per Control 3.1.")
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 13, "end_char": 45},
        quote="All access to PII must be logged",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_fact_checking_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single fact verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("fact_checking_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(inv_uid, "Company reported Q4 revenue of $10M.")
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 26, "end_char": 69},
        quote="The company reported revenue of $10M for Q4",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_internal_investigations_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single finding verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError(
            "internal_investigations_single_claim scenario requires at least 1 document"
        )

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(inv_uid, "Inappropriate material was reported on 2024-02-14.")
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 48, "end_char": 110},
        quote="receiving inappropriate material from Employee B on 2024-02-14",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_due_diligence_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single representation verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("due_diligence_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(
        inv_uid, "Target warrants no pending litigation as of date of letter."
    )
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 48, "end_char": 94},
        quote="no litigation is pending as of the date hereof",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def run_academic_single_claim(
    session, inv_uid: str, scenario: dict, trace: list[dict] | None = None
) -> None:
    """Execute single finding verification: one doc, one claim, one support link. No tension."""
    docs = scenario["documents"]
    if len(docs) < 1:
        raise ValueError("academic_single_claim scenario requires at least 1 document")

    content = docs[0]["content"].encode("utf-8")
    session.ingest_evidence(inv_uid, content, "text/plain")
    _trace_append(trace, 2, "ingest_evidence", 1)

    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid

    _, c_uid = session.propose_claim(
        inv_uid, "60% of participants showed improvement (Smith et al. 2023)."
    )
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 47, "end_char": 69},
        quote="60% showed improvement",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    _trace_append(trace, 3, "propose_claims", 1)
    _trace_append(trace, 3, "link_support", 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scenario validation driver for a scenario (rule-based; no AI/LLM)."
    )
    parser.add_argument(
        "--scenario",
        default="journalism_conflict",
        help="Scenario id (e.g. journalism_conflict). Default: journalism_conflict",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .chronicle path. Default: scripts/ai_validation/out/<scenario_id>.chronicle",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Write a run trace to reports/traces/<scenario_id>.json for propose_learn_from_trace.py (Phase 9).",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    scenario_id = scenario["id"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output or (OUT_DIR / f"{scenario_id}.chronicle")

    trace: list[dict] | None = [] if args.trace else None

    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    with tempfile.TemporaryDirectory(prefix="chronicle_ai_validation_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)

        with ChronicleSession(tmp_path) as session:
            session.create_investigation(
                f"Scenario validation: {scenario.get('name', scenario_id)}"
            )
            inv_uid = session.read_model.list_investigations()[0].investigation_uid
            if trace is not None:
                trace.append({"learn_step": 1, "action": "create_investigation"})

            if scenario_id == "journalism_conflict":
                run_journalism_conflict(session, inv_uid, scenario, trace)
            elif scenario_id == "journalism_single_claim":
                run_journalism_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "legal_conflict":
                run_legal_conflict(session, inv_uid, scenario, trace)
            elif scenario_id == "legal_single_claim":
                run_legal_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "compliance_single_claim":
                run_compliance_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "fact_checking_single_claim":
                run_fact_checking_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "internal_investigations_single_claim":
                run_internal_investigations_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "due_diligence_single_claim":
                run_due_diligence_single_claim(session, inv_uid, scenario, trace)
            elif scenario_id == "academic_single_claim":
                run_academic_single_claim(session, inv_uid, scenario, trace)
            else:
                raise ValueError(f"Unknown scenario: {scenario_id}")

            session.export_investigation(inv_uid, output_path)
            if trace is not None:
                trace.append({"learn_step": 6, "action": "export"})

    if trace is not None:
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        trace_path = TRACES_DIR / f"{scenario_id}.json"
        payload = {
            "scenario_id": scenario_id,
            "success": True,
            "recorded_at": datetime.now(UTC).isoformat(),
            "steps": trace,
        }
        trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Trace written to {trace_path}", file=__import__("sys").stderr)

    print(str(output_path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
