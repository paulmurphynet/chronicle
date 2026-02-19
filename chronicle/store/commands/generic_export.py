"""Generic export for integrations: JSON/CSL schema. Phase 7.1."""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Callable
from typing import Any, Protocol

from chronicle.eval_metrics import scorecard_to_metrics_dict
from chronicle.store.read_model import DefensibilityScorecard

GENERIC_EXPORT_SCHEMA_VERSION = 1
CLAIM_EVIDENCE_METRICS_SCHEMA_VERSION = 1


class ReadModelLike(Protocol):
    def get_investigation(self, uid: str) -> Any: ...
    def list_claims_by_type(
        self,
        claim_type: str | None = ...,
        investigation_uid: str | None = ...,
        limit: int | None = ...,
        include_withdrawn: bool = ...,
    ) -> list: ...
    def list_evidence_by_investigation(self, investigation_uid: str) -> list: ...
    def list_tensions(
        self, investigation_uid: str, *, status: str | None = ..., limit: int = ...
    ) -> list: ...
    def get_support_for_claim(self, claim_uid: str) -> list: ...
    def get_challenges_for_claim(self, claim_uid: str) -> list: ...
    def get_evidence_span(self, span_uid: str) -> Any: ...
    def get_evidence_item(self, evidence_uid: str) -> Any: ...
    def get_sources_backing_claim(self, claim_uid: str) -> list[dict[str, Any]]: ...


def _get_sources_backing_claim_safe(read_model: ReadModelLike, claim_uid: str) -> list[dict[str, Any]]:
    """Return sources_backing_claim when read_model supports it (includes independence_notes)."""
    try:
        result = read_model.get_sources_backing_claim(claim_uid)
    except AttributeError:
        return []
    return result if isinstance(result, list) else []


def _row_to_dict(obj: Any) -> dict[str, Any]:
    """Convert dataclass to dict for JSON (no recursion for nested objects)."""
    if obj is None:
        return {}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    return {}


def build_generic_export_json(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> dict[str, Any]:
    """Build generic export payload for one investigation. Phase 7.1. Documented in docs/GENERIC_EXPORT.md."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)
    return {
        "schema_version": GENERIC_EXPORT_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/GENERIC_EXPORT.md",
        "investigation": _row_to_dict(inv),
        "claims": [_row_to_dict(c) for c in claims],
        "evidence": [_row_to_dict(e) for e in evidence],
        "tensions": [_row_to_dict(t) for t in tensions],
    }


DefensibilityGetter = Callable[[str], DefensibilityScorecard | None]


def build_claim_evidence_metrics_export(
    read_model: ReadModelLike,
    get_defensibility_score: DefensibilityGetter,
    investigation_uid: str,
    *,
    claim_limit: int = 10_000,
) -> dict[str, Any]:
    """Build claim–evidence–metrics export for one investigation (stable JSON for fact-checking UIs).

    Returns a single JSON object with schema_version, investigation_uid, and a claims array. Each
    claim has claim_uid, claim_text, evidence_refs (evidence_uid, span_uid, link_type, uri),
    support_count, challenge_count, and defensibility (scorecard). Shape is defined in
    docs/claim-evidence-metrics-export.md.
    """
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    inv_uid = getattr(inv, "investigation_uid", investigation_uid)
    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid, limit=claim_limit
    )
    out_claims: list[dict[str, Any]] = []
    for c in claims:
        raw_claim_uid = getattr(c, "claim_uid", None)
        if not isinstance(raw_claim_uid, str) or not raw_claim_uid:
            continue
        claim_uid = raw_claim_uid
        claim_text = getattr(c, "claim_text", "") or ""
        support_links = read_model.get_support_for_claim(claim_uid)
        challenge_links = read_model.get_challenges_for_claim(claim_uid)
        evidence_refs: list[dict[str, Any]] = []
        for link in support_links + challenge_links:
            span = read_model.get_evidence_span(getattr(link, "span_uid", ""))
            evidence_uid = getattr(span, "evidence_uid", None) if span else None
            uri: str | None = None
            if evidence_uid:
                item = read_model.get_evidence_item(evidence_uid)
                uri = getattr(item, "uri", None) if item else None
            link_type = (getattr(link, "link_type", "") or "").replace("SUPPORTS", "SUPPORT").replace("CHALLENGES", "CHALLENGE")
            ref: dict[str, Any] = {
                "evidence_uid": evidence_uid or "",
                "link_type": link_type or "SUPPORT",
            }
            if getattr(link, "span_uid", None):
                ref["span_uid"] = link.span_uid
            if uri is not None:
                ref["uri"] = uri
            evidence_refs.append(ref)
        scorecard = get_defensibility_score(claim_uid)
        defensibility: dict[str, Any] = (
            scorecard_to_metrics_dict(claim_uid, scorecard) if scorecard else {}
        )
        claim_entry: dict[str, Any] = {
            "claim_uid": claim_uid,
            "claim_text": claim_text,
            "investigation_uid": inv_uid,
            "evidence_refs": evidence_refs,
            "support_count": len(support_links),
            "challenge_count": len(challenge_links),
            "defensibility": defensibility,
        }
        sources_backing = _get_sources_backing_claim_safe(read_model, claim_uid)
        if sources_backing:
            claim_entry["sources_backing_claim"] = sources_backing
        out_claims.append(claim_entry)
    return {
        "schema_version": CLAIM_EVIDENCE_METRICS_SCHEMA_VERSION,
        "schema_doc": "https://github.com/chronicle-app/chronicle/blob/main/docs/claim-evidence-metrics-export.md",
        "investigation_uid": inv_uid,
        "claims": out_claims,
    }


def build_generic_export_csv_zip(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> bytes:
    """Build a ZIP containing investigations.csv, claims.csv, evidence.csv, tensions.csv. Phase 7.1."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # investigations (one row)
        inv_dict = _row_to_dict(inv)
        if inv_dict:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=list(inv_dict.keys()), extrasaction="ignore")
            w.writeheader()
            w.writerow(inv_dict)
            zf.writestr("investigations.csv", out.getvalue())

        # claims
        keys = list(_row_to_dict(claims[0]).keys()) if claims else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for c in claims:
                w.writerow(_row_to_dict(c))
            zf.writestr("claims.csv", out.getvalue())

        # evidence
        keys = list(_row_to_dict(evidence[0]).keys()) if evidence else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for e in evidence:
                w.writerow(_row_to_dict(e))
            zf.writestr("evidence.csv", out.getvalue())

        # tensions
        keys = list(_row_to_dict(tensions[0]).keys()) if tensions else []
        if keys:
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for t in tensions:
                w.writerow(_row_to_dict(t))
            zf.writestr("tensions.csv", out.getvalue())

    return buf.getvalue()


# Phase 12: optional legal adapters (load file, exhibit list)

LOAD_FILE_COLUMNS = [
    "ControlNumber",
    "FilePath",
    "NativePath",
    "OriginalFileName",
    "FileSize",
    "Hash",
    "DocType",
    "CreatedAt",
]


def build_load_file_csv(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> str:
    """Build a load-file-style CSV for e-discovery tools. Phase 12. One row per evidence; ControlNumber = evidence_uid."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=LOAD_FILE_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for e in evidence:
        row = {
            "ControlNumber": getattr(e, "evidence_uid", ""),
            "FilePath": getattr(e, "uri", ""),
            "NativePath": getattr(e, "uri", ""),
            "OriginalFileName": getattr(e, "original_filename", ""),
            "FileSize": getattr(e, "file_size_bytes", 0),
            "Hash": getattr(e, "content_hash", ""),
            "DocType": getattr(e, "media_type", ""),
            "CreatedAt": getattr(e, "created_at", ""),
        }
        w.writerow(row)
    return out.getvalue()


EXHIBIT_LIST_COLUMNS = [
    "ExhibitNumber",
    "Type",
    "UID",
    "Label",
]


def build_exhibit_list_csv(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> str:
    """Build an exhibit-list-style CSV for legal (evidence + claims). Phase 12. ExhibitNumber is 1-based sequential."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=EXHIBIT_LIST_COLUMNS, extrasaction="ignore")
    w.writeheader()
    n = 1
    for e in evidence:
        label = getattr(e, "original_filename", "") or getattr(e, "evidence_uid", "")
        if len(label) > 120:
            label = label[:117] + "..."
        w.writerow(
            {
                "ExhibitNumber": n,
                "Type": "evidence",
                "UID": getattr(e, "evidence_uid", ""),
                "Label": label,
            }
        )
        n += 1
    for c in claims:
        if getattr(c, "current_status", "") == "WITHDRAWN":
            continue
        label = (getattr(c, "claim_text", "") or "")[:120]
        if len(getattr(c, "claim_text", "") or "") > 120:
            label = label + "..."
        w.writerow(
            {
                "ExhibitNumber": n,
                "Type": "claim",
                "UID": getattr(c, "claim_uid", ""),
                "Label": label,
            }
        )
        n += 1
    return out.getvalue()


# Phase E.2: GRC export (optional format for compliance/GRC platforms)

GRC_CONTROLS_COLUMNS = [
    "control_uid",
    "control_text",
    "claim_type",
    "status",
    "created_at",
    "updated_at",
]

GRC_EVIDENCE_COLUMNS = [
    "evidence_uid",
    "original_filename",
    "content_hash",
    "media_type",
    "created_at",
    "integrity_status",
]

GRC_EXCEPTIONS_COLUMNS = [
    "tension_uid",
    "status",
    "due_date",
    "assigned_to",
    "remediation_type",
    "created_at",
    "notes",
]


def build_grc_export_zip(
    read_model: ReadModelLike,
    investigation_uid: str,
) -> bytes:
    """Build a ZIP with GRC-oriented CSVs: controls (claims), evidence, exceptions (tensions). Phase E.2. See docs/GRC_EXPORT.md."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ValueError("Investigation not found")
    claims = read_model.list_claims_by_type(investigation_uid=investigation_uid, limit=10_000)
    evidence = read_model.list_evidence_by_investigation(investigation_uid)
    tensions = read_model.list_tensions(investigation_uid, limit=5000)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_CONTROLS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for c in claims:
            w.writerow(
                {
                    "control_uid": getattr(c, "claim_uid", ""),
                    "control_text": (getattr(c, "claim_text", "") or "")[:2000],
                    "claim_type": getattr(c, "claim_type", "") or "",
                    "status": getattr(c, "current_status", ""),
                    "created_at": getattr(c, "created_at", ""),
                    "updated_at": getattr(c, "updated_at", ""),
                }
            )
        zf.writestr("controls.csv", out.getvalue())

        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_EVIDENCE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for e in evidence:
            w.writerow(
                {
                    "evidence_uid": getattr(e, "evidence_uid", ""),
                    "original_filename": getattr(e, "original_filename", ""),
                    "content_hash": getattr(e, "content_hash", ""),
                    "media_type": getattr(e, "media_type", ""),
                    "created_at": getattr(e, "created_at", ""),
                    "integrity_status": getattr(e, "integrity_status", ""),
                }
            )
        zf.writestr("evidence.csv", out.getvalue())

        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=GRC_EXCEPTIONS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for t in tensions:
            w.writerow(
                {
                    "tension_uid": getattr(t, "tension_uid", ""),
                    "status": getattr(t, "status", ""),
                    "due_date": getattr(t, "due_date", "") or "",
                    "assigned_to": getattr(t, "assigned_to", "") or "",
                    "remediation_type": getattr(t, "remediation_type", "") or "",
                    "created_at": getattr(t, "created_at", ""),
                    "notes": getattr(t, "notes", "") or "",
                }
            )
        zf.writestr("exceptions.csv", out.getvalue())

    return buf.getvalue()
