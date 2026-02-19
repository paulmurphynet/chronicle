#!/usr/bin/env python3
"""Fail when generated frontend API routes are out of date."""

from __future__ import annotations

import difflib
import importlib.util
import tempfile
from pathlib import Path

TARGET = Path("frontend/src/lib/generated/routes.ts")

_GENERATOR_PATH = Path(__file__).resolve().parent / "generate_frontend_api_routes.py"
_SPEC = importlib.util.spec_from_file_location("generate_frontend_api_routes", _GENERATOR_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load generator module from {_GENERATOR_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
generate = _MODULE.generate


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="chronicle_routes_") as td:
        tmp_out = Path(td) / "routes.ts"
        generate(tmp_out)
        expected = tmp_out.read_text(encoding="utf-8")

    if not TARGET.exists():
        print(f"Missing generated file: {TARGET}")
        return 1
    actual = TARGET.read_text(encoding="utf-8")
    if actual == expected:
        print("Frontend API routes are up to date.")
        return 0

    print(f"Frontend API routes are out of date: {TARGET}")
    diff = difflib.unified_diff(
        actual.splitlines(),
        expected.splitlines(),
        fromfile=str(TARGET),
        tofile="generated",
        lineterm="",
    )
    for line in diff:
        print(line)
    print("Run: ./.venv/bin/python scripts/generate_frontend_api_routes.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
