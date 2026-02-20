#!/usr/bin/env python3
"""
VC/Data Integrity attestations -> Chronicle adapter.

This adapter records attestation references for claims, artifacts, and
checkpoints using existing Chronicle write commands. It stores attestation
metadata in event payload fields (`_verification_level`, `_attestation_ref`).

Expected input (JSON file or stdin): one object per line or single object.

{
  "investigation_uid": "optional existing inv uid",
  "attestations": [
    {
      "target_type": "claim",
      "claim_text": "A statement to track",
      "claim_type": "SEF",
      "verification_level": "verified_credential",
      "attestation_ref": "urn:vc:..."
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

create_project = import_module("chronicle.store.project").create_project
ChronicleSession = import_module("chronicle.store.session").ChronicleSession

_CLAIM_TYPES = frozenset({"SAC", "SEF", "INFERENCE", "UNKNOWN", "OPEN_QUESTION"})


def _as_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def run_one(obj: dict[str, Any], project_path: Path, actor_id: str = "vc-adapter") -> dict[str, Any]:
    """Run one VC/Data Integrity import payload and return summary result."""
    attestations = obj.get("attestations") or []
    if not isinstance(attestations, list) or not attestations:
        return {"error": "missing_attestations", "message": "field 'attestations' (array) is required"}
    inv_uid = _as_str(obj.get("investigation_uid"))

    if not project_path.joinpath("chronicle.db").exists():
        create_project(project_path)

    created_claims: list[str] = []
    created_artifacts: list[str] = []
    created_checkpoints: list[str] = []

    with ChronicleSession(project_path) as session:
        if not inv_uid:
            _, inv_uid = session.create_investigation(
                "VC/Data Integrity import",
                actor_id=actor_id,
                actor_type="tool",
            )
        elif session.read_model.get_investigation(inv_uid) is None:
            return {"error": "no_investigation", "message": f"investigation_uid not found: {inv_uid}"}

        for item in attestations:
            if not isinstance(item, dict):
                continue
            target_type = (_as_str(item.get("target_type")) or "claim").lower()
            verification_level = _as_str(item.get("verification_level"))
            attestation_ref = _as_str(item.get("attestation_ref"))

            if target_type == "claim":
                claim_text = _as_str(item.get("claim_text"))
                if not claim_text:
                    return {
                        "error": "missing_claim_text",
                        "message": "claim target requires non-empty 'claim_text'",
                    }
                claim_type = _as_str(item.get("claim_type"))
                if claim_type and claim_type not in _CLAIM_TYPES:
                    return {
                        "error": "invalid_claim_type",
                        "message": f"claim_type must be one of {sorted(_CLAIM_TYPES)}",
                    }
                _, claim_uid = session.propose_claim(
                    inv_uid,
                    claim_text,
                    initial_type=claim_type,
                    notes=_as_str(item.get("notes")),
                    actor_id=actor_id,
                    actor_type="tool",
                    verification_level=verification_level,
                    attestation_ref=attestation_ref,
                )
                created_claims.append(claim_uid)
                continue

            if target_type == "artifact":
                title = _as_str(item.get("title"))
                if not title:
                    return {
                        "error": "missing_artifact_title",
                        "message": "artifact target requires non-empty 'title'",
                    }
                _, artifact_uid = session.create_artifact(
                    inv_uid,
                    title,
                    artifact_type=_as_str(item.get("artifact_type")),
                    notes=_as_str(item.get("notes")),
                    actor_id=actor_id,
                    actor_type="tool",
                    workspace="forge",
                    verification_level=verification_level,
                    attestation_ref=attestation_ref,
                )
                created_artifacts.append(artifact_uid)
                continue

            if target_type == "checkpoint":
                scope_refs = item.get("scope_refs")
                if not isinstance(scope_refs, list) or not scope_refs:
                    return {
                        "error": "missing_scope_refs",
                        "message": "checkpoint target requires non-empty 'scope_refs' array",
                    }
                clean_scope_refs = [r for r in scope_refs if isinstance(r, str) and r.strip()]
                if not clean_scope_refs:
                    return {
                        "error": "missing_scope_refs",
                        "message": "checkpoint target requires non-empty 'scope_refs' array",
                    }
                artifact_refs_raw = item.get("artifact_refs")
                clean_artifact_refs = (
                    [r for r in artifact_refs_raw if isinstance(r, str) and r.strip()]
                    if isinstance(artifact_refs_raw, list)
                    else None
                )
                for ref in clean_scope_refs:
                    claim = session.read_model.get_claim(ref)
                    if claim is None:
                        continue
                    claim_type = getattr(claim, "claim_type", None)
                    if isinstance(claim_type, str) and claim_type.strip():
                        continue
                    session.type_claim(
                        ref,
                        "UNKNOWN",
                        actor_id=actor_id,
                        actor_type="tool",
                        workspace="forge",
                    )
                _, checkpoint_uid = session.create_checkpoint(
                    inv_uid,
                    clean_scope_refs,
                    artifact_refs=clean_artifact_refs,
                    reason=_as_str(item.get("reason")),
                    certifying_org_id=_as_str(item.get("certifying_org_id")),
                    certified_at=_as_str(item.get("certified_at")),
                    actor_id=actor_id,
                    actor_type="tool",
                    workspace="vault",
                    verification_level=verification_level,
                    attestation_ref=attestation_ref,
                )
                created_checkpoints.append(checkpoint_uid)
                continue

            return {
                "error": "invalid_target_type",
                "message": "target_type must be one of: claim, artifact, checkpoint",
            }

    return {
        "investigation_uid": inv_uid,
        "claims_created": len(created_claims),
        "artifacts_created": len(created_artifacts),
        "checkpoints_created": len(created_checkpoints),
        "verification_mode": "metadata_only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VC/Data Integrity attestations -> Chronicle (metadata-only compatibility path)."
    )
    parser.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    parser.add_argument("--path", type=Path, required=True, help="Project path")
    parser.add_argument("--actor-id", default="vc-adapter", help="Actor id for events")
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
