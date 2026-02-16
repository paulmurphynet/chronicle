"""Evidence citation export: BibTeX and CSL-JSON. Phase 6.1."""

import contextlib
import json
import re
from typing import Any

from chronicle.store.read_model.models import EvidenceItem


def _parse_metadata(evidence: EvidenceItem) -> dict[str, Any]:
    """Parse metadata_json and file_metadata_json into a dict."""
    out: dict[str, Any] = {}
    if evidence.metadata_json and evidence.metadata_json.strip():
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            out.update(json.loads(evidence.metadata_json))
    if evidence.file_metadata_json and evidence.file_metadata_json.strip():
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            out.update(json.loads(evidence.file_metadata_json))
    return out


def _bibtex_escape(s: str) -> str:
    """Escape BibTeX special characters."""
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("&", "\\&")


def evidence_to_bibtex(evidence: EvidenceItem) -> str:
    """Build a BibTeX entry for an evidence item. Phase 6.1."""
    meta = _parse_metadata(evidence)
    title = (
        meta.get("title") or evidence.original_filename or evidence.evidence_uid or "Untitled"
    ).strip()
    author = (meta.get("author") or "").strip() or "Unknown"
    year = ""
    if meta.get("published_at"):
        year = str(meta["published_at"])[:4]
    elif meta.get("captured_at"):
        year = str(meta["captured_at"])[:4]
    elif evidence.created_at and len(evidence.created_at) >= 4:
        year = evidence.created_at[:4]
    cite_key = re.sub(r"[^a-zA-Z0-9_-]", "_", evidence.evidence_uid)[:64]
    lines = [
        f"@misc{{{cite_key},",
        f"  title = {{{_bibtex_escape(title)} }},",
        f"  author = {{{_bibtex_escape(author)} }},",
    ]
    if year:
        lines.append(f"  year = {{{year}}},")
    lines.append(f"  note = {{Chronicle evidence UID: {evidence.evidence_uid}}}")
    lines.append("}")
    return "\n".join(lines)


def evidence_to_csl(evidence: EvidenceItem) -> dict[str, Any]:
    """Build a CSL-JSON item for an evidence item. Phase 6.1."""
    meta = _parse_metadata(evidence)
    title = (
        meta.get("title") or evidence.original_filename or evidence.evidence_uid or "Untitled"
    ).strip()
    author = (meta.get("author") or "").strip() or "Unknown"
    year = None
    if meta.get("published_at"):
        year = (
            int(str(meta["published_at"])[:4]) if str(meta["published_at"])[:4].isdigit() else None
        )
    elif meta.get("captured_at"):
        year = int(str(meta["captured_at"])[:4]) if str(meta["captured_at"])[:4].isdigit() else None
    elif evidence.created_at and evidence.created_at[:4].isdigit():
        year = int(evidence.created_at[:4])
    return {
        "id": evidence.evidence_uid,
        "type": "document",
        "title": title,
        "author": [{"family": author, "given": ""}] if author else [],
        "issued": {"date-parts": [[year]]} if year else {},
        "note": f"Chronicle evidence UID: {evidence.evidence_uid}",
    }
