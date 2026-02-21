#!/usr/bin/env python3
"""Generate frontend route constants from FastAPI OpenAPI metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ts_key(operation_id: str) -> str:
    # Keep generator stable and readable in TS object keys.
    cleaned = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in operation_id)
    return cleaned


def generate(output: Path) -> None:
    try:
        from chronicle.api.app import app
    except ImportError as exc:
        raise RuntimeError(
            "Generating frontend API routes requires API dependencies. "
            "Install with: pip install -e '.[api]'"
        ) from exc

    spec = app.openapi()
    paths = spec.get("paths") or {}

    entries: list[tuple[str, str, str]] = []
    for path, methods in sorted(paths.items()):
        if not isinstance(methods, dict):
            continue
        for method, info in sorted(methods.items()):
            if not isinstance(info, dict):
                continue
            operation_id = str(info.get("operationId") or f"{method}_{path}")
            entries.append((_ts_key(operation_id), method.upper(), path))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        f.write("// Auto-generated from chronicle.api.app OpenAPI.\n")
        f.write("// Regenerate with: ./.venv/bin/python scripts/generate_frontend_api_routes.py\n\n")
        f.write("export const ROUTES = {\n")
        for op_id, _method, path in entries:
            f.write(f"  {op_id}: '{path}',\n")
        f.write("} as const\n\n")
        f.write("export const ROUTE_METHODS = {\n")
        for op_id, method, _path in entries:
            f.write(f"  {op_id}: '{method}',\n")
        f.write("} as const\n\n")
        f.write("export type RouteName = keyof typeof ROUTES\n")
        f.write("export type ApiRoute = (typeof ROUTES)[RouteName]\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate frontend API routes from OpenAPI")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "frontend/src/lib/generated/routes.ts",
        help="Output TypeScript file",
    )
    args = parser.parse_args()
    generate(args.output)
