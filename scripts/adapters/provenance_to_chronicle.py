#!/usr/bin/env python3
"""
Provenance assertions → Chronicle adapter.

Reads provenance assertions (e.g. "this evidence from this source/model") and
creates Chronicle sources and evidence–source links. We record what you give us;
we do not verify C2PA/CR or that evidence actually came from the source.
See docs/provenance-recording.md.

Expected input (JSON file or stdin): one object per line or single object.

  {
    "investigation_uid": "existing inv_uid (or omit to create one)",
    "assertions": [
      {
        "source_uid": "optional; if missing we generate",
        "source_display_name": "Reuters",
        "source_type": "organization",
        "evidence_content": "base64 or plain text",
        "evidence_media_type": "text/plain",
        "evidence_filename": "doc.txt"
      }
    ]
  }

Or minimal: { "assertions": [ { "source_display_name": "Model: gpt-4", "evidence_content": "The quote..." } ] }

For each assertion we: register_source (or reuse by source_uid), ingest_evidence,
link_evidence_to_source. Run from repo root with an existing project:

  PYTHONPATH=. python3 scripts/adapters/provenance_to_chronicle.py --path /path/to/project [input.json]
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import uuid
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

create_project = import_module("chronicle.store.project").create_project
ChronicleSession = import_module("chronicle.store.session").ChronicleSession


def decode_content(raw: str, b64: bool = False) -> bytes:
    if b64:
        return base64.b64decode(raw)
    return raw.encode("utf-8")


def run_one(obj: dict, project_path: Path, actor_id: str = "provenance-adapter") -> dict:
    assertions = obj.get("assertions") or []
    inv_uid = obj.get("investigation_uid")
    if not assertions:
        return {"error": "missing_assertions", "message": "field 'assertions' (array) is required"}

    if not project_path.joinpath("chronicle.db").exists():
        create_project(project_path)
    with ChronicleSession(project_path) as session:
        if not inv_uid:
            _, inv_uid = session.create_investigation(
                "Provenance import",
                actor_id=actor_id,
                actor_type="tool",
            )
        else:
            if session.read_model.get_investigation(inv_uid) is None:
                return {"error": "no_investigation", "message": f"investigation_uid not found: {inv_uid}"}
        created_sources: list[str] = []
        created_links: int = 0
        for a in assertions:
            if not isinstance(a, dict):
                continue
            name = (a.get("source_display_name") or a.get("source_uid") or str(uuid.uuid4())[:8]).strip()
            source_type = (a.get("source_type") or "other").strip()
            if source_type not in ("person", "organization", "document", "public_record", "anonymous_tip", "other"):
                source_type = "other"
            source_uid = a.get("source_uid")
            if not source_uid:
                _, source_uid = session.register_source(
                    inv_uid,
                    name,
                    source_type=source_type,
                    actor_id=actor_id,
                    actor_type="tool",
                    workspace="forge",
                )
                created_sources.append(source_uid)
            content = a.get("evidence_content")
            if content is None:
                continue
            blob = decode_content(content, a.get("evidence_content_base64", False))
            media_type = a.get("evidence_media_type") or "text/plain"
            filename = a.get("evidence_filename") or "provenance.txt"
            _, ev_uid = session.ingest_evidence(
                inv_uid,
                blob,
                media_type,
                original_filename=filename,
                metadata=a.get("metadata"),
                actor_id=actor_id,
                actor_type="tool",
            )
            session.link_evidence_to_source(
                ev_uid,
                source_uid,
                actor_id=actor_id,
                actor_type="tool",
                workspace="forge",
            )
            created_links += 1
        return {
            "investigation_uid": inv_uid,
            "sources_created": len(created_sources),
            "evidence_source_links_created": created_links,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provenance assertions → Chronicle (sources, evidence, evidence–source links). We record; we do not verify."
    )
    parser.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    parser.add_argument("--path", type=Path, required=True, help="Project path (must exist or will be created)")
    parser.add_argument("--actor-id", default="provenance-adapter", help="Actor id for events")
    args = parser.parse_args()
    raw = Path(args.input).read_text() if args.input else sys.stdin.read()
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        print(json.dumps({"error": "no_input", "message": "empty input"}))
        return 1
    args.path.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": "invalid_json", "message": str(e)}))
            exit_code = 1
            continue
        result = run_one(obj, args.path, actor_id=args.actor_id)
        print(json.dumps(result))
        if result.get("error"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
