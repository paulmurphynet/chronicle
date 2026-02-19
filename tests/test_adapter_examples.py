from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

check_examples = import_module("scripts.adapters.check_examples")
validator = import_module("scripts.adapters.validate_adapter_outputs")
starter = import_module("scripts.adapters.starter_batch_to_scorer")

EXAMPLES_DIR = REPO_ROOT / "scripts" / "adapters" / "examples"


def test_validator_passes_checked_in_scored_example() -> None:
    scored = EXAMPLES_DIR / "scored_runs_example.jsonl"
    assert scored.is_file()
    rc = validator.main(["--input", str(scored)])
    assert rc == 0


def test_starter_and_validator_on_checked_in_harness_example(tmp_path: Path) -> None:
    harness = EXAMPLES_DIR / "harness_runs_valid.jsonl"
    out = tmp_path / "scored_generated.jsonl"
    assert harness.is_file()
    rc = starter.main(["--input", str(harness), "--output", str(out)])
    assert rc == 0
    assert out.is_file()
    rc = validator.main(["--input", str(out)])
    assert rc == 0


def test_check_examples_script_passes() -> None:
    rc = check_examples.main(["--examples-dir", str(EXAMPLES_DIR)])
    assert rc == 0
