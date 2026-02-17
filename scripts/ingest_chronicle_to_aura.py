"""
Ingest a verified .chronicle file into the shared graph project and sync to Neo4j (e.g. Aura).

Pipeline: verify → import into CHRONICLE_GRAPH_PROJECT → neo4j-sync.

Requires: .chronicle file path. Env: NEO4J_URI, NEO4J_PASSWORD (and optionally NEO4J_USER,
CHRONICLE_GRAPH_PROJECT). Install: pip install -e ".[neo4j]". Optional: python-dotenv to load .env.

Usage (from repo root):

  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py path/to/file.chronicle
  CHRONICLE_GRAPH_PROJECT=/path/to/project PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle

See docs/aura-graph-pipeline.md for full runbook and Aura setup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Optional: load .env from repo root so NEO4J_* and CHRONICLE_GRAPH_PROJECT are set
def _load_dotenv() -> None:
    try:
        import dotenv  # noqa: F401
        from dotenv import load_dotenv
        repo_root = Path(__file__).resolve().parent.parent
        load_dotenv(repo_root / ".env")
    except ImportError:
        pass


def main() -> int:
    _load_dotenv()

    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/ingest_chronicle_to_aura.py <path/to/file.chronicle> [--project PATH]",
            file=sys.stderr,
        )
        return 1

    chronicle_path = Path(sys.argv[1])
    if not chronicle_path.is_file():
        print(f"Error: not a file: {chronicle_path}", file=sys.stderr)
        return 1
    if chronicle_path.suffix != ".chronicle":
        print(f"Error: expected .chronicle file, got: {chronicle_path}", file=sys.stderr)
        return 1

    project_dir = os.environ.get("CHRONICLE_GRAPH_PROJECT")
    if project_dir is None or project_dir == "":
        repo_root = Path(__file__).resolve().parent.parent
        project_dir = str(repo_root / "chronicle_graph_project")
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    # 1. Verify
    from tools.verify_chronicle.verify_chronicle import verify_chronicle_file

    results = verify_chronicle_file(chronicle_path, run_invariants=True)
    failed = [r for r in results if not r[1]]
    if failed:
        print("Verification failed:", file=sys.stderr)
        for name, passed, detail in failed:
            print(f"  {name}: {detail}", file=sys.stderr)
        return 1
    print(f"Verified: {chronicle_path.name}")

    # 2. Import into graph project
    from chronicle.store.export_import import import_investigation

    import_investigation(chronicle_path, project_path)
    print(f"Imported into {project_path}")

    # 3. Sync to Neo4j
    uri = os.environ.get("NEO4J_URI", "").strip()
    user = os.environ.get("NEO4J_USER", "neo4j").strip() or "neo4j"
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri:
        print(
            "Error: NEO4J_URI not set. Set NEO4J_URI (and NEO4J_PASSWORD) in .env or environment.",
            file=sys.stderr,
        )
        return 1
    if not password:
        print(
            "Error: NEO4J_PASSWORD not set. Set NEO4J_PASSWORD in .env or environment.",
            file=sys.stderr,
        )
        return 1

    try:
        from chronicle.store.neo4j_sync import sync_project_to_neo4j
    except ImportError as e:
        print(
            "Error: Neo4j driver not installed. Run: pip install -e \".[neo4j]\"",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    sync_project_to_neo4j(project_path, uri, user, password)
    print("Synced to Neo4j.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
