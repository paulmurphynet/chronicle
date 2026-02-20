#!/usr/bin/env python3
"""
C2PA assertions -> Chronicle adapter.

This adapter records C2PA assertion references in evidence metadata and links
evidence to sources. It does not cryptographically verify C2PA assertions by
itself; status is recorded as provided (or defaults to not_verified).

Expected input (JSON file or stdin): one object per line or single object.

{
  "investigation_uid": "optional existing inv uid",
  "assertions": [
    {
      "source_display_name": "Camera A",
      "source_type": "document",
      "evidence_content": "raw or base64 text/blob",
      "evidence_content_base64": false,
      "evidence_media_type": "image/jpeg",
      "evidence_filename": "frame-01.jpg",
      "c2pa_claim_id": "urn:uuid:...",
      "c2pa_assertion_id": "assertion-123",
      "c2pa_manifest_digest": "sha256:...",
      "c2pa_verification_status": "not_verified"
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

run_provenance_one = import_module("scripts.adapters.provenance_to_chronicle").run_one

_C2PA_METADATA_KEYS = (
    "c2pa_claim_id",
    "c2pa_assertion_id",
    "c2pa_manifest_digest",
    "c2pa_manifest_url",
    "c2pa_issuer",
    "c2pa_signer",
    "c2pa_generator",
    "c2pa_signature_algorithm",
    "c2pa_assertion_hash",
    "c2pa_validation_report_uri",
)

_STATUS_VALUES = frozenset({"verified", "failed", "not_verified", "unknown"})


def _normalize_status(raw: Any) -> str:
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in _STATUS_VALUES:
            return value
    return "not_verified"


def _transform_payload(obj: dict[str, Any]) -> dict[str, Any]:
    """Transform C2PA assertion input into provenance_to_chronicle input shape."""
    assertions = obj.get("assertions") or []
    transformed: list[dict[str, Any]] = []
    for item in assertions:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        base_metadata: dict[str, Any] = metadata.copy() if isinstance(metadata, dict) else {}
        for key in _C2PA_METADATA_KEYS:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            base_metadata[key] = value
        base_metadata["c2pa_verification_status"] = _normalize_status(
            item.get("c2pa_verification_status")
        )
        base_metadata.setdefault("c2pa_recording_mode", "metadata_only")

        transformed.append(
            {
                "source_uid": item.get("source_uid"),
                "source_display_name": item.get("source_display_name"),
                "source_type": item.get("source_type"),
                "evidence_content": item.get("evidence_content"),
                "evidence_content_base64": item.get("evidence_content_base64", False),
                "evidence_media_type": item.get("evidence_media_type"),
                "evidence_filename": item.get("evidence_filename"),
                "metadata": base_metadata,
            }
        )
    return {
        "investigation_uid": obj.get("investigation_uid"),
        "assertions": transformed,
    }


def run_one(obj: dict[str, Any], project_path: Path, actor_id: str = "c2pa-adapter") -> dict[str, Any]:
    """Run one C2PA import payload and return summary result."""
    transformed = _transform_payload(obj)
    result = run_provenance_one(transformed, project_path, actor_id=actor_id)
    if result.get("error"):
        return result
    assertions = transformed.get("assertions") or []
    return {
        **result,
        "c2pa_assertions_recorded": len(assertions),
        "verification_mode": "metadata_only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="C2PA assertions -> Chronicle (metadata + source links). We record; we do not verify."
    )
    parser.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    parser.add_argument("--path", type=Path, required=True, help="Project path")
    parser.add_argument("--actor-id", default="c2pa-adapter", help="Actor id for events")
    args = parser.parse_args(argv)

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        print(json.dumps({"error": "no_input", "message": "empty input"}))
        return 1

    args.path.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            print(json.dumps({"error": "invalid_json", "message": str(exc)}))
            exit_code = 1
            continue
        if not isinstance(obj, dict):
            print(json.dumps({"error": "invalid_input", "message": "top-level JSON must be object"}))
            exit_code = 1
            continue
        result = run_one(obj, args.path, actor_id=args.actor_id)
        print(json.dumps(result))
        if result.get("error"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
