from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def test_whitepaper_publication_metadata_shape() -> None:
    metadata_path = Path("docs/whitepaper-publication-metadata.json")
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert isinstance(payload["document_id"], str) and payload["document_id"]
    assert (
        isinstance(payload["canonical_document_path"], str) and payload["canonical_document_path"]
    )
    assert isinstance(payload["current_revision"], str) and payload["current_revision"]

    revisions = payload.get("revisions")
    assert isinstance(revisions, list) and revisions
    revision_ids = {item["revision"] for item in revisions if isinstance(item, dict)}
    assert payload["current_revision"] in revision_ids

    for item in revisions:
        assert isinstance(item["revision"], str) and item["revision"]
        assert isinstance(item["published_at"], str) and item["published_at"]
        date.fromisoformat(item["published_at"])
        assert isinstance(item["status"], str) and item["status"]
        assert isinstance(item["document_path"], str) and item["document_path"]
        assert isinstance(item["citation"], dict)
        assert isinstance(item["citation"].get("apa"), str) and item["citation"]["apa"]
        assert isinstance(item["citation"].get("bibtex"), str) and item["citation"]["bibtex"]
