from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.supply_chain_gate")


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _npm_report(*, high: int = 0, critical: int = 0) -> dict[str, object]:
    return {
        "metadata": {
            "vulnerabilities": {
                "info": 0,
                "low": 0,
                "moderate": 0,
                "high": high,
                "critical": critical,
                "total": high + critical,
            }
        }
    }


def test_supply_chain_gate_rejects_npm_error_payload(tmp_path: Path) -> None:
    pip_report = _write(
        tmp_path / "pip.json",
        [{"name": "requests", "version": "2.31.0", "vulns": []}],
    )
    npm_report = _write(
        tmp_path / "npm.json",
        {"error": {"code": "ENOLOCK", "summary": "lockfile required"}},
    )
    rc = module.main(
        [
            "--pip-report",
            str(pip_report),
            "--npm-report",
            str(npm_report),
        ]
    )
    assert rc == 2


def test_supply_chain_gate_rejects_empty_pip_dependencies(tmp_path: Path) -> None:
    pip_report = _write(tmp_path / "pip.json", {"dependencies": [], "fixes": []})
    npm_report = _write(tmp_path / "npm.json", _npm_report())
    rc = module.main(
        [
            "--pip-report",
            str(pip_report),
            "--npm-report",
            str(npm_report),
        ]
    )
    assert rc == 2


def test_supply_chain_gate_threshold_enforced(tmp_path: Path) -> None:
    pip_report = _write(
        tmp_path / "pip.json",
        [{"name": "pydantic", "version": "2.0.0", "vulns": [{"id": "X"}]}],
    )
    npm_report = _write(tmp_path / "npm.json", _npm_report(high=1, critical=0))
    rc = module.main(
        [
            "--pip-report",
            str(pip_report),
            "--npm-report",
            str(npm_report),
            "--max-python-vulns",
            "0",
            "--max-high",
            "0",
            "--max-critical",
            "0",
        ]
    )
    assert rc == 1


def test_supply_chain_gate_passes_valid_clean_reports(tmp_path: Path) -> None:
    pip_report = _write(
        tmp_path / "pip.json",
        [{"name": "requests", "version": "2.31.0", "vulns": []}],
    )
    npm_report = _write(tmp_path / "npm.json", _npm_report())
    rc = module.main(
        [
            "--pip-report",
            str(pip_report),
            "--npm-report",
            str(npm_report),
        ]
    )
    assert rc == 0
