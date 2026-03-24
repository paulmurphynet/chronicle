#!/usr/bin/env python3
"""Run the Chronicle conformance test on a .chronicle file (T4.4).

Usage:
  PYTHONPATH=. python3 scripts/run_conformance.py path/to/file.chronicle
  PYTHONPATH=. python3 scripts/run_conformance.py path/to/file.chronicle --json

Exit 0 = file is conformant (all checks pass). Exit 1 = not conformant.
With --json, prints a single JSON object: { "verified": bool, "checks": [...], "summary": {...}? }.
Without --json, delegates to the reference verifier (same output as chronicle-verify).
"""

import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

# Allow running from repo root without installing (ruff: E402 allowed for path setup)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.verify_chronicle.verify_chronicle import (  # noqa: E402
    _summary_from_chronicle,
    verify_chronicle_file,
)


def main() -> int:
    args = [a for a in sys.argv[1:] if a not in ("--json",)]
    json_out = "--json" in sys.argv[1:]
    if not args:
        print(
            "Usage: PYTHONPATH=. python3 scripts/run_conformance.py <path/to/file.chronicle> [--json]",
            file=sys.stderr,
        )
        return 2
    path = Path(args[0])
    run_invariants = "--no-invariants" not in sys.argv[1:]
    results = verify_chronicle_file(path, run_invariants=run_invariants)
    all_passed = all(r[1] for r in results)

    if json_out:
        out = {
            "verified": all_passed,
            "checks": [{"name": n, "passed": p, "detail": d} for n, p, d in results],
        }
        if all_passed:
            try:
                with (
                    zipfile.ZipFile(path, "r") as zf,
                    tempfile.TemporaryDirectory(prefix="chronicle_verify_") as tmp,
                ):
                    db_path = Path(tmp) / "chronicle.db"
                    db_path.write_bytes(zf.read("chronicle.db"))
                    conn = sqlite3.connect(str(db_path))
                    try:
                        out["summary"] = _summary_from_chronicle(zf, conn)
                    finally:
                        conn.close()
            except Exception:
                pass
        print(json.dumps(out))
        return 0 if all_passed else 1

    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    print("")
    if all_passed:
        print("Result: VERIFIED")
        return 0
    print("Result: NOT VERIFIED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
