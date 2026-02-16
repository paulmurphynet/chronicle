#!/usr/bin/env python3
"""Check internal relative links in Markdown docs.

Finds [text](path) and [text](path#anchor) where path is relative (no scheme).
Resolves path relative to each file and reports missing targets.

Run from repo root: python3 scripts/check_doc_links.py [path]
Default path is docs/. Exit code 1 if any broken links.
"""

import argparse
import re
import sys
from pathlib import Path


# Match [text](url) with url not starting with http://, https://, mailto:, #
LINK_PATTERN = re.compile(
    r"\]\s*\(\s*(?!https?://|mailto:)([^#)\s]+)(?:#([^)]*))?\s*\)"
)


def get_links(content: str) -> list[tuple[str, str | None]]:
    """Return list of (path, anchor) from relative links in content."""
    out = []
    for m in LINK_PATTERN.finditer(content):
        path_part = m.group(1).strip()
        anchor = m.group(2)
        if path_part.startswith("#"):
            continue
        out.append((path_part, anchor))
    return out


def check_doc_links(root: Path) -> list[tuple[Path, str, str | None, str]]:
    """Check all .md under root. Return list of (file, link_path, anchor, error)."""
    root = root.resolve()
    errors: list[tuple[Path, str, str | None, str]] = []
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append((path, "", None, str(e)))
            continue
        base_dir = path.parent
        for link_path, anchor in get_links(content):
            # Resolve relative to current file's directory
            target = (base_dir / link_path).resolve()
            if not target.suffix:
                target = target.with_suffix(".md")
            if not target.exists():
                errors.append((path, link_path, anchor, "target not found"))
            elif not target.is_file():
                errors.append((path, link_path, anchor, "target is not a file"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="docs", help="Directory to check (default: docs)")
    args = parser.parse_args()
    root = Path(args.path)
    if not root.exists():
        print(f"Error: {root} does not exist", file=sys.stderr)
        return 1
    errors = check_doc_links(root)
    if not errors:
        print("No broken internal links found.")
        return 0
    for path, link_path, anchor, err in errors:
        loc = f"{path}: {link_path}"
        if anchor:
            loc += f"#{anchor}"
        print(f"{loc} - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
