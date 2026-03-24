from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from chronicle.store.commands.generic_export import (
    build_generic_export_csv_zip,
    build_generic_export_json,
    validate_generic_export_csv_zip,
    validate_generic_export_json,
)
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def _seed_investigation(project_path: Path) -> tuple[str, str]:
    with ChronicleSession(project_path) as session:
        _, inv_uid = session.create_investigation(
            "Generic export contract", actor_id="t", actor_type="tool"
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Contract evidence text.",
            "text/plain",
            original_filename="contract.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 8},
            quote="Contract",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "Contract claim.", actor_id="t", actor_type="tool"
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
    return inv_uid, claim_uid


def test_generic_export_json_contract_passes(tmp_path: Path) -> None:
    create_project(tmp_path)
    inv_uid, claim_uid = _seed_investigation(tmp_path)
    with ChronicleSession(tmp_path) as session:
        payload = build_generic_export_json(session.read_model, inv_uid)
    errors = validate_generic_export_json(payload)
    assert errors == []
    assert payload["investigation"]["investigation_uid"] == inv_uid
    assert any(c["claim_uid"] == claim_uid for c in payload["claims"])


def test_generic_export_json_contract_detects_mismatch(tmp_path: Path) -> None:
    create_project(tmp_path)
    inv_uid, _ = _seed_investigation(tmp_path)
    with ChronicleSession(tmp_path) as session:
        payload = build_generic_export_json(session.read_model, inv_uid)
    payload["claims"][0]["investigation_uid"] = "inv_other"
    errors = validate_generic_export_json(payload)
    assert any("must match investigation_uid" in err for err in errors)


def test_generic_export_csv_contract_passes_and_detects_tamper(tmp_path: Path) -> None:
    create_project(tmp_path)
    inv_uid, _ = _seed_investigation(tmp_path)
    with ChronicleSession(tmp_path) as session:
        payload = build_generic_export_csv_zip(session.read_model, inv_uid)
    assert validate_generic_export_csv_zip(payload) == []

    # Tamper by removing a required CSV file.
    with zipfile.ZipFile(BytesIO(payload), "r") as zin:
        names = zin.namelist()
        blobs = {name: zin.read(name) for name in names if name != "claims.csv"}
    out_buf = BytesIO()
    with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, blob in blobs.items():
            zout.writestr(name, blob)
    errors = validate_generic_export_csv_zip(out_buf.getvalue())
    assert errors
