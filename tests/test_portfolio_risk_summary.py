from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

portfolio_module = import_module("scripts.portfolio_risk_summary")


def _build_project_with_portfolio_variance(project_dir: Path) -> dict[str, str]:
    create_project(project_dir)
    uids: dict[str, str] = {}
    with ChronicleSession(project_dir) as session:
        _, inv_a = session.create_investigation("Inv A", actor_id="t", actor_type="tool")
        _, claim_a = session.propose_claim(inv_a, "Claim A", actor_id="t", actor_type="tool")
        session.record_human_confirm(
            "claim",
            claim_a,
            "editorial_review",
            "Reviewed and accepted.",
            actor_id="reviewer",
            actor_type="human",
        )
        uids["inv_a"] = inv_a

        _, inv_b = session.create_investigation("Inv B", actor_id="t", actor_type="tool")
        _, claim_b1 = session.propose_claim(inv_b, "Claim B1", actor_id="t", actor_type="tool")
        _, claim_b2 = session.propose_claim(inv_b, "Claim B2", actor_id="t", actor_type="tool")
        session.declare_tension(
            inv_b,
            claim_b1,
            claim_b2,
            workspace="forge",
            actor_id="reviewer",
            actor_type="human",
        )
        session.record_human_override(
            claim_b1,
            "defensibility_warning",
            "Proceed while collecting corroboration.",
            actor_id="reviewer",
            actor_type="human",
        )
        uids["inv_b"] = inv_b

        _, inv_c = session.create_investigation("Inv C", actor_id="t", actor_type="tool")
        _, claim_c = session.propose_claim(inv_c, "Claim C", actor_id="t", actor_type="tool")
        session.record_human_override(
            claim_c,
            "defensibility_warning",
            "First override.",
            actor_id="reviewer",
            actor_type="human",
        )
        session.record_human_override(
            claim_c,
            "defensibility_warning",
            "Second override.",
            actor_id="reviewer",
            actor_type="human",
        )
        uids["inv_c"] = inv_c
    return uids


def test_portfolio_risk_summary_aggregates_unresolved_and_overrides(tmp_path: Path) -> None:
    uids = _build_project_with_portfolio_variance(tmp_path)

    payload = portfolio_module.build_portfolio_risk_summary(tmp_path)
    aggregate = payload["aggregate"]

    assert aggregate["total_investigations"] == 3
    assert aggregate["total_unresolved_tensions"] == 1
    assert aggregate["investigations_with_unresolved_tensions"] == 1
    assert aggregate["total_human_overrides"] == 3
    assert aggregate["investigations_with_human_overrides"] == 2
    assert aggregate["override_concentration"]["top_investigation_uid"] == uids["inv_c"]
    assert aggregate["override_concentration"]["top_investigation_override_count"] == 2
    assert aggregate["override_concentration"]["top_investigation_share"] == 0.6667

    by_uid = {row["investigation_uid"]: row for row in payload["investigations"]}
    assert by_uid[uids["inv_b"]]["metrics"]["unresolved_tensions_count"] == 1
    assert by_uid[uids["inv_c"]]["metrics"]["human_overrode_count"] == 2


def test_portfolio_risk_summary_has_deterministic_ranking(tmp_path: Path) -> None:
    uids = _build_project_with_portfolio_variance(tmp_path)

    first = portfolio_module.build_portfolio_risk_summary(tmp_path)
    second = portfolio_module.build_portfolio_risk_summary(tmp_path)

    first_ranked = [row["investigation_uid"] for row in first["investigations"]]
    second_ranked = [row["investigation_uid"] for row in second["investigations"]]
    assert first_ranked == second_ranked
    assert first_ranked[0] == uids["inv_b"]
    assert first_ranked[1] == uids["inv_c"]


def test_portfolio_risk_summary_main_writes_output(tmp_path: Path) -> None:
    _build_project_with_portfolio_variance(tmp_path)
    out = tmp_path / "portfolio_summary.json"

    rc = portfolio_module.main(
        [
            "--path",
            str(tmp_path),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["aggregate"]["total_investigations"] == 3
