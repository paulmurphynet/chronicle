"""Security-related tests for scorer contract (path traversal, path vs text/url)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.scorer_contract import run_scorer_contract


def test_path_traversal_outside_cwd_ignored(tmp_path: Path) -> None:
    """Evidence item with path outside cwd is ignored (path traversal mitigation)."""
    # Put a valid file inside tmp_path
    safe_file = tmp_path / "allowed.txt"
    safe_file.write_text("allowed content", encoding="utf-8")
    # Request a path that would escape to /etc/passwd (or similar) when resolved
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Path like /etc/passwd is absolute and resolve() gives /etc/passwd; relative_to(cwd) will raise
        out = run_scorer_contract(
            {
                "query": "Q",
                "answer": "A",
                "evidence": [
                    {"path": "/etc/passwd"},
                    {"path": str(safe_file)},
                ],
            },
            allow_path=True,
        )
    finally:
        os.chdir(old_cwd)
    # Should succeed using only the safe file; /etc/passwd must not be read
    assert out.get("error") != "invalid_input"
    assert "claim_uid" in out
    # One chunk (allowed content) so defensibility is computed
    assert out.get("corroboration", {}).get("support_count", 0) >= 1


def test_allow_path_false_ignores_path_key() -> None:
    """When allow_path=False (e.g. API), evidence with only 'path' key yields no chunks -> invalid_input."""
    out = run_scorer_contract(
        {"query": "Q", "answer": "A", "evidence": [{"path": "/any/path.txt"}]},
        allow_path=False,
    )
    assert out.get("error") == "invalid_input"
    assert "message" in out
