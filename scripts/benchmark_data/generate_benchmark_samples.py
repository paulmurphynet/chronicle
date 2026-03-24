"""
Generate small public benchmark dataset: 6 synthetic .chronicle files with different
defensibility profiles for evaluation and research reproducibility. P6.1.2 / D.8.
Output: docs/benchmark/sample_investigations/
Run from repo root: PYTHONPATH=. python3 scripts/benchmark_data/generate_benchmark_samples.py
"""

import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "benchmark" / "sample_investigations"
PROFILE_SOURCE = REPO_ROOT / "docs" / "spec" / "profiles" / "policy_investigative_journalism.json"

# Scenario 1: conflicting location (London vs Paris) — claims, support, one open tension
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

# Scenario 2: single claim, two supporting evidence — no tension (strong)
EVIDENCE_A = "Meeting minutes: the board approved the budget on 2024-02-01. Vote was unanimous."
EVIDENCE_B = "Treasurer memo: budget approval completed 2024-02-01. All signatories recorded."

# Scenario 3: weak — one claim, one support (single source)
EVIDENCE_WEAK = "Internal note 2024-03-10: the contract was signed. No other corroboration on file."

# Scenario 4: challenged — one claim, one support + one challenge
EVIDENCE_SUPPORT = "Press release: the product launched on 2024-04-01. Available in all regions."
EVIDENCE_CHALLENGE = (
    "Support ticket log: regional rollout delayed; EU availability from 2024-04-15 only."
)

# Scenario 5: resolved tension — two claims, tension then resolved with rationale
EVIDENCE_R1 = "Q1 report: revenue was $2M. Audited figures."
EVIDENCE_R2 = "Correction notice: Q1 revenue restated to $1.8M after adjustment. Dated 2024-05-01."

# Scenario 6: strong — one claim, three supporting evidence (high corroboration)
EVIDENCE_S1 = "Witness 1 statement: the meeting took place at 10:00 on 2024-06-01."
EVIDENCE_S2 = "Witness 2 statement: the meeting was at 10:00 on 2024-06-01."
EVIDENCE_S3 = "Calendar entry: meeting scheduled 2024-06-01 10:00. Confirmed."


def make_conflict_sample(session, inv_uid: str, out_path: Path) -> None:
    """One investigation: London vs Paris claims, support links, one open tension."""
    session.ingest_evidence(inv_uid, EVIDENCE_1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_2.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_3.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid, ev2_uid = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c1_uid = session.propose_claim(inv_uid, "Subject was in London on 2024-01-15.")
    _, c2_uid = session.propose_claim(inv_uid, "Subject was in Paris on 2024-01-15.")
    session.propose_claim(
        inv_uid, "Conflicting location reports must be resolved before publication."
    )
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
    session.declare_tension(inv_uid, c1_uid, c2_uid, workspace="forge")
    session.export_investigation(inv_uid, out_path)


def make_single_claim_sample(session, inv_uid: str, out_path: Path) -> None:
    """One investigation: single claim with two supporting evidence spans, no tension."""
    session.ingest_evidence(inv_uid, EVIDENCE_A.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_B.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid, ev2_uid = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "The board approved the budget on 2024-02-01.")
    _, span1_uid = session.anchor_span(
        inv_uid,
        ev1_uid,
        "text_offset",
        {"start_char": 27, "end_char": 58},
        quote="the board approved the budget on 2024-02-01",
    )
    session.link_support(inv_uid, span1_uid, c_uid)
    _, span2_uid = session.anchor_span(
        inv_uid,
        ev2_uid,
        "text_offset",
        {"start_char": 24, "end_char": 54},
        quote="budget approval completed 2024-02-01",
    )
    session.link_support(inv_uid, span2_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


def make_weak_single_source_sample(session, inv_uid: str, out_path: Path) -> None:
    """One claim, one supporting evidence — weak/single-source defensibility profile."""
    session.ingest_evidence(inv_uid, EVIDENCE_WEAK.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_uid = evidence[0].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "The contract was signed on or before 2024-03-10.")
    _, span_uid = session.anchor_span(
        inv_uid,
        ev_uid,
        "text_offset",
        {"start_char": 28, "end_char": 52},
        quote="the contract was signed",
    )
    session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


def make_challenged_sample(session, inv_uid: str, out_path: Path) -> None:
    """One claim with one support and one challenge — challenged defensibility profile."""
    session.ingest_evidence(inv_uid, EVIDENCE_SUPPORT.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_CHALLENGE.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev_sup_uid, ev_ch_uid = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c_uid = session.propose_claim(inv_uid, "The product launched in all regions on 2024-04-01.")
    _, span_sup = session.anchor_span(
        inv_uid,
        ev_sup_uid,
        "text_offset",
        {"start_char": 22, "end_char": 58},
        quote="the product launched on 2024-04-01. Available in all regions",
    )
    _, span_ch = session.anchor_span(
        inv_uid,
        ev_ch_uid,
        "text_offset",
        {"start_char": 24, "end_char": 68},
        quote="EU availability from 2024-04-15 only",
    )
    session.link_support(inv_uid, span_sup, c_uid)
    session.link_challenge(inv_uid, span_ch, c_uid)
    session.export_investigation(inv_uid, out_path)


def make_resolved_tension_sample(session, inv_uid: str, out_path: Path) -> None:
    """Two claims (restated revenue), tension declared then resolved with rationale."""
    session.ingest_evidence(inv_uid, EVIDENCE_R1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_R2.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid, ev2_uid = evidence[0].evidence_uid, evidence[1].evidence_uid
    _, c1_uid = session.propose_claim(inv_uid, "Q1 revenue was $2M.")
    _, c2_uid = session.propose_claim(inv_uid, "Q1 revenue was restated to $1.8M.")
    _, span1 = session.anchor_span(
        inv_uid,
        ev1_uid,
        "text_offset",
        {"start_char": 14, "end_char": 28},
        quote="revenue was $2M",
    )
    _, span2 = session.anchor_span(
        inv_uid,
        ev2_uid,
        "text_offset",
        {"start_char": 38, "end_char": 62},
        quote="Q1 revenue restated to $1.8M",
    )
    session.link_support(inv_uid, span1, c1_uid)
    session.link_support(inv_uid, span2, c2_uid)
    _, tension_uid = session.declare_tension(
        inv_uid,
        c1_uid,
        c2_uid,
        tension_kind="source_conflict_unadjudicated",
        workspace="forge",
    )
    session.update_tension_status(
        tension_uid,
        "RESOLVED",
        reason="Restatement supersedes initial figure; $1.8M is the audited final figure.",
        workspace="forge",
    )
    session.export_investigation(inv_uid, out_path)


def make_strong_three_sources_sample(session, inv_uid: str, out_path: Path) -> None:
    """One claim with three supporting evidence — strong corroboration profile."""
    session.ingest_evidence(inv_uid, EVIDENCE_S1.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_S2.encode("utf-8"), "text/plain")
    session.ingest_evidence(inv_uid, EVIDENCE_S3.encode("utf-8"), "text/plain")
    evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    ev1_uid, ev2_uid, ev3_uid = (
        evidence[0].evidence_uid,
        evidence[1].evidence_uid,
        evidence[2].evidence_uid,
    )
    _, c_uid = session.propose_claim(inv_uid, "The meeting took place at 10:00 on 2024-06-01.")
    for ev_uid, start, end, quote in [
        (ev1_uid, 24, 52, "the meeting took place at 10:00 on 2024-06-01"),
        (ev2_uid, 24, 52, "the meeting was at 10:00 on 2024-06-01"),
        (ev3_uid, 22, 50, "meeting scheduled 2024-06-01 10:00"),
    ]:
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": start, "end_char": end},
            quote=quote,
        )
        session.link_support(inv_uid, span_uid, c_uid)
    session.export_investigation(inv_uid, out_path)


def main() -> None:
    from chronicle.core.policy import POLICY_FILENAME
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    samples = [
        ("Benchmark sample: conflicting claims", make_conflict_sample, "sample_conflict.chronicle"),
        (
            "Benchmark sample: single claim, two supports",
            make_single_claim_sample,
            "sample_single_claim.chronicle",
        ),
        (
            "Benchmark sample: weak single source",
            make_weak_single_source_sample,
            "sample_weak_single_source.chronicle",
        ),
        (
            "Benchmark sample: challenged (support + challenge)",
            make_challenged_sample,
            "sample_challenged.chronicle",
        ),
        (
            "Benchmark sample: resolved tension",
            make_resolved_tension_sample,
            "sample_resolved_tension.chronicle",
        ),
        (
            "Benchmark sample: strong three sources",
            make_strong_three_sources_sample,
            "sample_strong_three_sources.chronicle",
        ),
    ]

    with tempfile.TemporaryDirectory(prefix="chronicle_benchmark_") as tmp:
        tmp_path = Path(tmp)
        create_project(tmp_path)
        if PROFILE_SOURCE.is_file():
            shutil.copy(PROFILE_SOURCE, tmp_path / POLICY_FILENAME)
        with ChronicleSession(tmp_path) as session:
            for i, (title, make_fn, out_name) in enumerate(samples):
                session.create_investigation(title)
                inv_uid = session.read_model.list_investigations()[i].investigation_uid
                make_fn(session, inv_uid, tmp_path / out_name)

        for _, _, out_name in samples:
            (OUTPUT_DIR / out_name).write_bytes((tmp_path / out_name).read_bytes())
    print(f"Written {len(samples)} files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
