#!/usr/bin/env python3
"""Check that key docs include current, required workflow references."""

from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_SNIPPETS: dict[str, list[str]] = {
    "README.md": [
        "run_defensibility_benchmark.py --mode session",
    ],
    "docs/getting-started.md": [
        "run_defensibility_benchmark.py --mode session",
    ],
    "docs/rag-in-5-minutes.md": [
        "run_defensibility_benchmark.py --mode session",
    ],
    "docs/trust-metrics.md": [
        "run_defensibility_benchmark.py \\",
        "--mode session",
    ],
    "docs/reference-workflows.md": [
        "scripts/run_reference_workflows.py",
        "scripts/adapters/starter_batch_to_scorer.py",
        "scripts/adapters/validate_adapter_outputs.py",
        "scripts/adapters/check_examples.py",
    ],
    "docs/integration-acceptance-checklist.md": [
        "scripts/adapters/validate_adapter_outputs.py",
        "scripts/adapters/check_examples.py",
        "scripts/check_integration_export_contracts.py",
    ],
    "docs/ci-branch-protection.md": [
        "scripts/check_branch_protection_rollout.py",
    ],
    "docs/production-readiness-checklist.md": [
        "scripts/check_branch_protection_rollout.py",
        "reports/branch_protection_rollout_report.json",
    ],
    "lessons/07-integrations-and-scripts.md": [
        "starter_batch_to_scorer.py",
        "validate_adapter_outputs.py",
        "scripts/adapters/check_examples.py",
    ],
    "lessons/10-export-import-neo4j.md": [
        "scripts/check_neo4j_contract.py",
    ],
    "lessons/quizzes/quiz-07-integrations-and-scripts.md": [
        "starter_batch_to_scorer.py",
        "validate_adapter_outputs.py",
    ],
    "lessons/quizzes/quiz-10-export-import-neo4j.md": [
        "scripts/check_neo4j_contract.py",
    ],
    "scripts/adapters/README.md": [
        "mapping_profile_nested.json",
        "harness_runs_nested.jsonl",
        "scripts/adapters/check_examples.py",
    ],
}


def run_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path, snippets in REQUIRED_SNIPPETS.items():
        path = repo_root / rel_path
        if not path.is_file():
            errors.append(f"Missing required doc file: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"Missing snippet in {rel_path}: {snippet}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check docs for required current references.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    errors = run_checks(repo_root)
    if errors:
        print("Docs currency check failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Docs currency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
