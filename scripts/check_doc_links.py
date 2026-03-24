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

# Match markdown links [text](target) with no whitespace between "](" so checklist
# items like "[ ] (Optional)" are not treated as links.
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)#]+)(?:#([^)]*))?\)")
SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def get_links(content: str) -> list[tuple[str, str | None]]:
    """Return list of (path, anchor) from relative links in content."""
    out: list[tuple[str, str | None]] = []
    for m in LINK_PATTERN.finditer(content):
        path_part = m.group(1).strip()
        anchor = m.group(2)
        if not path_part or path_part.startswith("#"):
            continue
        if SCHEME_PATTERN.match(path_part):
            continue
        out.append((path_part, anchor))
    return out


def _target_exists(base_dir: Path, link_path: str) -> bool:
    """Return True when the markdown link resolves to an existing local target."""
    raw_target = (base_dir / link_path).resolve()
    if raw_target.exists():
        return True
    # Common shorthand in docs: link without extension points to markdown file.
    if not raw_target.suffix and raw_target.with_suffix(".md").exists():
        return True
    # Directory links are common in this repo (e.g., ../docs/).
    return bool(raw_target.is_dir())


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
            if not _target_exists(base_dir, link_path):
                errors.append((path, link_path, anchor, "target not found"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", default="docs", help="Directory to check (default: docs)"
    )
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
