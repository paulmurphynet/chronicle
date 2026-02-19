from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_check_module = import_module("scripts.check_neo4j_contract")
_ingest_module = import_module("scripts.ingest_chronicle_to_aura")

run_checks = _check_module.run_checks
parse_ingest_args = _ingest_module._parse_args


def test_neo4j_contract_check_passes() -> None:
    errors = run_checks(REPO_ROOT)
    assert errors == []


def test_ingest_cli_parses_project_and_dedupe_flag() -> None:
    args = parse_ingest_args(
        [
            "example.chronicle",
            "--project",
            "chronicle_graph_project",
            "--dedupe-evidence-by-content-hash",
        ]
    )
    assert str(args.chronicle_file).endswith("example.chronicle")
    assert str(args.project).endswith("chronicle_graph_project")
    assert args.dedupe_evidence_by_content_hash is True
