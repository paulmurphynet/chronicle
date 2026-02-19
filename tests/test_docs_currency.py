from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

docs_currency = import_module("scripts.check_docs_currency")


def test_docs_currency_check_passes() -> None:
    errors = docs_currency.run_checks(REPO_ROOT)
    assert errors == []
