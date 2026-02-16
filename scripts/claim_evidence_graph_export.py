"""
Export claim–evidence graph as Mermaid or Graphviz (E.3).

Run from repo root:

  PYTHONPATH=. python3 scripts/claim_evidence_graph_export.py --path /path/to/project --investigation inv_xxx
  PYTHONPATH=. python3 scripts/claim_evidence_graph_export.py --path /path/to/project --investigation inv_xxx --claim claim_yyy
  PYTHONPATH=. python3 scripts/claim_evidence_graph_export.py --path /path/to/project --investigation inv_xxx --format dot

Optional --claim: show only one claim and its supporting/challenging evidence.
Optional --format: mermaid (default) or dot (Graphviz).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _mermaid_id(uid: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", uid)[:50]


def _mermaid_label(text: str, max_len: int = 50) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return escaped[:max_len] if len(escaped) > max_len else escaped


def _dot_id(uid: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", uid)[:50]


def _dot_label(text: str, max_len: int = 40) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return escaped[:max_len] + ("..." if len(escaped) > max_len else "")


def build_graph(session, investigation_uid: str, claim_uid: str | None):
    """Return (nodes, edges). nodes = [(id, label, type)], edges = [(from_id, to_id, type)]."""
    rm = session.read_model
    if rm.get_investigation(investigation_uid) is None:
        return [], []

    claims = rm.list_claims_by_type(
        investigation_uid=investigation_uid, include_withdrawn=False, limit=500
    )
    if claim_uid:
        claims = [c for c in claims if c.claim_uid == claim_uid]
        if not claims:
            return [], []

    evidence_uids: set[str] = set()
    edges: list[tuple[str, str, str]] = []

    for c in claims:
        for link in rm.get_support_for_claim(c.claim_uid) + rm.get_challenges_for_claim(c.claim_uid):
            span = rm.get_evidence_span(link.span_uid)
            if span:
                evidence_uids.add(span.evidence_uid)
                edge_type = "support" if link.link_type == "SUPPORTS" else "challenge"
                edges.append((c.claim_uid, span.evidence_uid, edge_type))

    nodes: list[tuple[str, str, str]] = []
    for c in claims:
        label = (c.claim_text or c.claim_uid)[:80]
        if len(c.claim_text or "") > 80:
            label += "..."
        nodes.append((c.claim_uid, label, "claim"))
    for ev_uid in evidence_uids:
        ev = rm.get_evidence_item(ev_uid)
        label = (getattr(ev, "uri", None) or ev_uid) if ev else ev_uid
        if isinstance(label, str) and len(label) > 40:
            label = label[:40] + "..."
        nodes.append((ev_uid, label or ev_uid, "evidence"))

    return nodes, edges


def emit_mermaid(nodes: list[tuple[str, str, str]], edges: list[tuple[str, str, str]]) -> str:
    lines = ["flowchart LR"]
    seen: set[str] = set()
    for nid, label, ntype in nodes:
        id_ = _mermaid_id(nid)
        if id_ in seen:
            continue
        seen.add(id_)
        safe = _mermaid_label(label)
        if ntype == "claim":
            lines.append(f'  {id_}["{safe}"]')
        else:
            lines.append(f'  {id_}("{safe}")')
    for from_id, to_id, etype in edges:
        fid, tid = _mermaid_id(from_id), _mermaid_id(to_id)
        if fid in seen and tid in seen:
            if etype == "support":
                lines.append(f"  {fid} -->|support| {tid}")
            else:
                lines.append(f"  {fid} -.->|challenge| {tid}")
    return "\n".join(lines)


def emit_dot(nodes: list[tuple[str, str, str]], edges: list[tuple[str, str, str]]) -> str:
    lines = ["digraph claim_evidence {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    seen: set[str] = set()
    for nid, label, ntype in nodes:
        id_ = _dot_id(nid)
        if id_ in seen:
            continue
        seen.add(id_)
        safe = _dot_label(label)
        shape = "box" if ntype == "claim" else "ellipse"
        lines.append(f'  {id_} [label="{safe}", shape={shape}];')
    for from_id, to_id, etype in edges:
        fid, tid = _dot_id(from_id), _dot_id(to_id)
        if fid in seen and tid in seen:
            style = "solid" if etype == "support" else "dashed"
            lines.append(f'  {fid} -> {tid} [label="{etype}", style={style}];')
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export claim–evidence graph as Mermaid or Graphviz (E.3)."
    )
    parser.add_argument("--path", type=Path, required=True, help="Chronicle project path")
    parser.add_argument(
        "--investigation",
        required=True,
        help="Investigation UID",
    )
    parser.add_argument(
        "--claim",
        default=None,
        help="Optional: limit to one claim and its evidence",
    )
    parser.add_argument(
        "--format",
        choices=["mermaid", "dot"],
        default="mermaid",
        help="Output format (default: mermaid)",
    )
    args = parser.parse_args()

    if not args.path.is_dir():
        print("Error: --path must be an existing directory", file=sys.stderr)
        return 1

    from chronicle.store.session import ChronicleSession

    if not (args.path / "chronicle.db").exists():
        print("Error: chronicle.db not found in project path", file=sys.stderr)
        return 1

    with ChronicleSession(args.path) as session:
        nodes, edges = build_graph(session, args.investigation, args.claim)

    if not nodes and not edges:
        print("No claims or links found.", file=sys.stderr)
        return 0

    if args.format == "mermaid":
        print(emit_mermaid(nodes, edges))
    else:
        print(emit_dot(nodes, edges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
