#!/usr/bin/env python3
"""Normalize Unicode curly/smart quotes and em-dash to ASCII in Markdown docs.

Replaces:
  U+2018 ' (left single)   -> U+0027 '
  U+2019 ' (right single)  -> U+0027 '
  U+201C " (left double)   -> U+0022 "
  U+201D " (right double)  -> U+0022 "
  U+2014 — (em dash)       -> " - " (space-hyphen-space)

Run from repo root: python3 scripts/normalize_quotes_in_docs.py [--dry-run] [--em-dash] [--verbose] [path]

If path is omitted, defaults to docs/. Use --dry-run to print changes without writing.
Default is quotes only. Use --em-dash to also replace em-dash (U+2014) with " - ".
"""

import argparse
import sys
from pathlib import Path

REPLACEMENTS_QUOTES = [
    ("\u2018", "'"),  # left single quotation mark -> ASCII apostrophe
    ("\u2019", "'"),  # right single quotation mark -> ASCII apostrophe
    ("\u201c", '"'),  # left double quotation mark -> ASCII double quote
    ("\u201d", '"'),  # right double quotation mark -> ASCII double quote
]

REPLACEMENTS_EMDASH = [
    ("\u2014", " - "),  # em dash -> space-hyphen-space
]


def normalize(text: str, em_dash: bool = False) -> str:
    for old, new in REPLACEMENTS_QUOTES:
        text = text.replace(old, new)
    if em_dash:
        for old, new in REPLACEMENTS_EMDASH:
            text = text.replace(old, new)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would change, do not write"
    )
    parser.add_argument(
        "--em-dash", action="store_true", help="Also replace em-dash (U+2014) with ' - '"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print every file scanned")
    parser.add_argument(
        "path", nargs="?", default="docs", help="Directory or file to process (default: docs)"
    )
    args = parser.parse_args()
    root = Path(args.path)
    if not root.exists():
        print(f"Error: {root} does not exist", file=sys.stderr)
        return 1
    files = list(root.rglob("*.md")) if root.is_dir() else [root]
    changed = 0
    for path in sorted(files):
        if not path.is_file():
            continue
        try:
            orig = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skip {path}: {e}", file=sys.stderr)
            continue
        new = normalize(orig, em_dash=args.em_dash)
        if new != orig:
            changed += 1
            if args.dry_run:
                print(path)
            else:
                path.write_text(new, encoding="utf-8")
                print(path)
        elif args.verbose:
            print(path)
    if args.dry_run and changed:
        print(f"(dry run: {changed} file(s) would be updated)")
    elif changed:
        print(f"Updated {changed} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
