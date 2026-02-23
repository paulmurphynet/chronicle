from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.check_post_public_finalization")


def _branch_report(status: str) -> dict:
    return {"status": status}


def _neo4j_report(status: str, *, ok: bool = True) -> dict:
    event_status = bool(ok and status == "passed")
    return {
        "status": status,
        "events": [
            {"event": "push", "ok": event_status},
            {"event": "pull_request", "ok": event_status},
        ],
    }


def _standards_log(*, sent: bool) -> dict:
    status = "sent" if sent else "prepared"
    sent_at = "2026-02-23T00:00:00Z" if sent else "pending"
    return {
        "outreach_status": "sent" if sent else "prepared_pending_public_repo",
        "venues": [
            {
                "venue": "w3c_linked_data",
                "status": status,
                "sent_at": sent_at,
                "contact": "reviewer-a@example.org",
            },
            {
                "venue": "c2pa_ecosystem",
                "status": status,
                "sent_at": sent_at,
                "contact": "reviewer-b@example.org",
            },
            {
                "venue": "applied_research",
                "status": status,
                "sent_at": sent_at,
                "contact": "reviewer-c@example.org",
            },
        ],
    }


def test_post_public_finalization_passes_when_all_checks_pass() -> None:
    report = module.run_check(
        branch_protection_report=_branch_report("passed"),
        neo4j_ci_report=_neo4j_report("passed"),
        standards_dispatch_log=_standards_log(sent=True),
        required_venues=module.REQUIRED_VENUES,
    )
    assert report["status"] == "passed"
    assert all(check["passed"] is True for check in report["checks"])


def test_post_public_finalization_fails_when_standards_not_sent() -> None:
    report = module.run_check(
        branch_protection_report=_branch_report("passed"),
        neo4j_ci_report=_neo4j_report("passed"),
        standards_dispatch_log=_standards_log(sent=False),
        required_venues=module.REQUIRED_VENUES,
    )
    assert report["status"] == "failed"
    standards = next(c for c in report["checks"] if c["name"] == "external_standards_dispatch")
    assert standards["status"] == "failed"
    assert standards["passed"] is False


def test_post_public_finalization_blocked_when_venue_missing() -> None:
    log = _standards_log(sent=True)
    log["venues"] = log["venues"][:-1]

    report = module.run_check(
        branch_protection_report=_branch_report("passed"),
        neo4j_ci_report=_neo4j_report("passed"),
        standards_dispatch_log=log,
        required_venues=module.REQUIRED_VENUES,
    )
    assert report["status"] == "blocked"
    standards = next(c for c in report["checks"] if c["name"] == "external_standards_dispatch")
    assert standards["status"] == "blocked"
