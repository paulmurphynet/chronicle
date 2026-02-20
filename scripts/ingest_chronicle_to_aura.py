"""
Ingest a verified .chronicle file into the shared graph project and sync to Neo4j (e.g. Aura).

Pipeline: verify → import into CHRONICLE_GRAPH_PROJECT → neo4j-sync.

Requires: .chronicle file path. Env: NEO4J_URI, NEO4J_PASSWORD (and optionally NEO4J_USER,
CHRONICLE_GRAPH_PROJECT). Install: pip install -e ".[neo4j]". Optional: python-dotenv to load .env.

Usage (from repo root):

  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py path/to/file.chronicle
  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle --project /path/to/project
  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle --dedupe-evidence-by-content-hash
  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle --database neo4j --max-retries 5

See docs/aura-graph-pipeline.md for full runbook and Aura setup.
"""

from __future__ import annotations

import argparse
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a .chronicle file, import it into a shared Chronicle graph project, "
            "and sync to Neo4j."
        )
    )
    parser.add_argument("chronicle_file", type=Path, help="Path to .chronicle file")
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help=(
            "Graph project directory (default: CHRONICLE_GRAPH_PROJECT env var, "
            "or ./chronicle_graph_project)"
        ),
    )
    parser.add_argument(
        "--dedupe-evidence-by-content-hash",
        action="store_true",
        help=(
            "Enable Neo4j sync dedupe mode (one EvidenceItem per content_hash and "
            "one Claim per hash(claim_text))."
        ),
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Neo4j database name (default: NEO4J_DATABASE env or server default)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max retries for transient sync errors (default: NEO4J_SYNC_MAX_RETRIES or 3)",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=None,
        help="Base retry backoff in seconds (default: NEO4J_SYNC_RETRY_BACKOFF_SECONDS or 1.0)",
    )
    parser.add_argument(
        "--connection-timeout-seconds",
        type=float,
        default=None,
        help="Neo4j connection timeout in seconds (default: NEO4J_CONNECTION_TIMEOUT_SECONDS or 15)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = _parse_args(argv)

    chronicle_path = args.chronicle_file
    if not chronicle_path.is_file():
        print(f"Error: not a file: {chronicle_path}", file=sys.stderr)
        return 1
    if chronicle_path.suffix != ".chronicle":
        print(f"Error: expected .chronicle file, got: {chronicle_path}", file=sys.stderr)
        return 1

    if args.project is not None:
        project_dir = str(args.project)
    else:
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
        for name, _passed, detail in failed:
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
    database = (args.database or os.environ.get("NEO4J_DATABASE", "")).strip() or None
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
            'Error: Neo4j driver not installed. Run: pip install -e ".[neo4j]"',
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    sync_project_to_neo4j(
        project_path,
        uri,
        user,
        password,
        dedupe_evidence_by_content_hash=args.dedupe_evidence_by_content_hash,
        database=database,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        connection_timeout_seconds=args.connection_timeout_seconds,
    )
    print("Synced to Neo4j.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
