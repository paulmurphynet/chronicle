#!/usr/bin/env python3
"""Validate adapter example files and starter->validator flow."""

from __future__ import annotations

import argparse
import sys
import tempfile
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

starter_main = import_module("scripts.adapters.starter_batch_to_scorer").main
validator_main = import_module("scripts.adapters.validate_adapter_outputs").main


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check adapter examples and starter/validator flow.")
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "examples",
        help="Adapter examples directory",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    examples_dir = args.examples_dir.resolve()
    harness_path = examples_dir / "harness_runs_valid.jsonl"
    scored_path = examples_dir / "scored_runs_example.jsonl"

    if not harness_path.is_file():
        print(f"Missing example file: {harness_path}")
        return 1
    if not scored_path.is_file():
        print(f"Missing example file: {scored_path}")
        return 1

    code = validator_main(["--input", str(scored_path)])
    if code != 0:
        print("Static scored example failed contract validation.")
        return 1

    with tempfile.TemporaryDirectory(prefix="chronicle_adapter_examples_") as tmp:
        generated_path = Path(tmp) / "generated_scored.jsonl"
        code = starter_main(
            [
                "--input",
                str(harness_path),
                "--output",
                str(generated_path),
            ]
        )
        if code != 0:
            print("Starter adapter failed on valid harness example input.")
            return 1
        code = validator_main(["--input", str(generated_path)])
        if code != 0:
            print("Generated scored output failed contract validation.")
            return 1

    print("Adapter example checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
