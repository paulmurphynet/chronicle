"""Chronicle MCP server."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from chronicle.mcp.service import ChronicleMcpService


def build_mcp_server(
    *,
    project_path: Path,
    name: str = "Chronicle MCP",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> Any:
    """Build and configure the FastMCP server for Chronicle."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised in envs without MCP extra
        raise RuntimeError(
            "MCP support requires optional dependency 'mcp'. "
            "Install with: pip install 'chronicle-standard[mcp]'"
        ) from exc

    service = ChronicleMcpService(project_path)
    mcp = FastMCP(
        name=name,
        instructions=(
            "Chronicle tools for evidence-first investigations: create investigations, ingest evidence, "
            "propose claims, link support/challenges, compute defensibility, and export .chronicle bundles."
        ),
        host=host,
        port=port,
        dependencies=["chronicle-standard[mcp]"],
    )

    @mcp.tool(description="Create a Chronicle investigation.")
    def chronicle_create_investigation(
        title: str,
        description: str | None = None,
        investigation_key: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        return service.create_investigation(
            title=title,
            description=description,
            investigation_key=investigation_key,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    @mcp.tool(description="List Chronicle investigations.")
    def chronicle_list_investigations(
        limit: int = 20,
        is_archived: bool | None = None,
    ) -> dict[str, Any]:
        return service.list_investigations(limit=limit, is_archived=is_archived)

    @mcp.tool(
        description="Ingest text evidence and auto-anchor a full-text span. Returns evidence_uid and span_uid."
    )
    def chronicle_ingest_evidence_text(
        investigation_uid: str,
        text: str,
        original_filename: str = "evidence.txt",
        media_type: str = "text/plain",
        provenance_type: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        return service.ingest_evidence_text(
            investigation_uid=investigation_uid,
            text=text,
            original_filename=original_filename,
            media_type=media_type,
            provenance_type=provenance_type,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    @mcp.tool(description="Propose a claim in an investigation.")
    def chronicle_propose_claim(
        investigation_uid: str,
        claim_text: str,
        initial_type: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        return service.propose_claim(
            investigation_uid=investigation_uid,
            claim_text=claim_text,
            initial_type=initial_type,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    @mcp.tool(description="List claims in an investigation.")
    def chronicle_list_claims(
        investigation_uid: str,
        include_withdrawn: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        return service.list_claims(
            investigation_uid=investigation_uid,
            include_withdrawn=include_withdrawn,
            limit=limit,
        )

    @mcp.tool(description="Link an evidence span as SUPPORTS to a claim.")
    def chronicle_link_support(
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        rationale: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        return service.link_support(
            investigation_uid=investigation_uid,
            span_uid=span_uid,
            claim_uid=claim_uid,
            rationale=rationale,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    @mcp.tool(description="Link an evidence span as CHALLENGES to a claim.")
    def chronicle_link_challenge(
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        rationale: str | None = None,
        defeater_kind: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        return service.link_challenge(
            investigation_uid=investigation_uid,
            span_uid=span_uid,
            claim_uid=claim_uid,
            rationale=rationale,
            defeater_kind=defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    @mcp.tool(description="Get defensibility scorecard for a claim.")
    def chronicle_get_defensibility(claim_uid: str) -> dict[str, Any] | None:
        return service.get_defensibility(claim_uid=claim_uid)

    @mcp.tool(description="Get reasoning brief for a claim.")
    def chronicle_get_reasoning_brief(
        claim_uid: str,
        limit: int = 200,
    ) -> dict[str, Any] | None:
        return service.get_reasoning_brief(claim_uid=claim_uid, limit=limit)

    @mcp.tool(description="Export an investigation to a .chronicle file.")
    def chronicle_export_investigation(
        investigation_uid: str,
        output_path: str,
    ) -> dict[str, Any]:
        return service.export_investigation(
            investigation_uid=investigation_uid,
            output_path=output_path,
        )

    return mcp


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Chronicle MCP server.")
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path(os.environ.get("CHRONICLE_PROJECT_PATH", ".")).resolve(),
        help="Chronicle project directory (default: CHRONICLE_PROJECT_PATH or current directory).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transports.")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transports.")
    parser.add_argument("--name", default="Chronicle MCP", help="Server display name.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    server = build_mcp_server(
        project_path=args.project_path,
        name=args.name,
        host=args.host,
        port=args.port,
    )
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
