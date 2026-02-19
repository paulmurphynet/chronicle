#!/usr/bin/env python3
"""Validate a release tag against pyproject version."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

TAG_RE = re.compile(r"^v?(\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?)$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release tag matches pyproject version")
    parser.add_argument("--tag", required=True, help="Release tag (e.g. v0.1.0)")
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml",
    )
    args = parser.parse_args()

    if not args.pyproject.is_file():
        print(f"pyproject not found: {args.pyproject}", file=sys.stderr)
        return 1

    with args.pyproject.open("rb") as f:
        pyproject = tomllib.load(f)
    version = str(pyproject.get("project", {}).get("version", "")).strip()
    if not version:
        print("project.version missing in pyproject.toml", file=sys.stderr)
        return 1

    match = TAG_RE.match(args.tag.strip())
    if not match:
        print("Tag must match v<semver> or <semver>, e.g. v0.1.0", file=sys.stderr)
        return 1

    tag_version = match.group(1)
    if tag_version != version:
        print(
            f"Tag/version mismatch: tag={tag_version!r} pyproject={version!r}",
            file=sys.stderr,
        )
        return 1

    print(f"Release tag validated: {args.tag} -> version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
