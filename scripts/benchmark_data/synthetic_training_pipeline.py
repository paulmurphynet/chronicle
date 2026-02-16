"""
Synthetic training data pipeline (M8, experimental): generate investigations at scale,
write to Chronicle, export to JSONL for training.

Runs (1) generate_vertical_corpora to produce N journalism + M legal .chronicle files,
(2) imports all into one Chronicle project, (3) export_for_ml to produce one JSONL.
Template-based only (no LLM). Start small (e.g. 1k investigations).

Usage (from repo root):

  PYTHONPATH=. python3 scripts/benchmark_data/synthetic_training_pipeline.py --output synthetic_1k.jsonl

  # Smaller run
  PYTHONPATH=. python3 scripts/benchmark_data/synthetic_training_pipeline.py --journalism 100 --legal 100 --output synthetic_200.jsonl

  # Keep the Chronicle project for inspection
  PYTHONPATH=. python3 scripts/benchmark_data/synthetic_training_pipeline.py --project /path/to/project --output out.jsonl

See docs/chronicle-as-training-data.md and docs/benchmark.md Section 2.3.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic training pipeline: generate -> Chronicle -> export JSONL (experimental)."
    )
    parser.add_argument("--journalism", type=int, default=500, help="Number of journalism investigations")
    parser.add_argument("--legal", type=int, default=500, help="Number of legal investigations")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL path")
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Keep project at this path (default: temp dir, deleted after export)",
    )
    args = parser.parse_args()

    if args.journalism < 0 or args.legal < 0:
        print("--journalism and --legal must be non-negative.", file=sys.stderr)
        return 1

    total = args.journalism + args.legal
    if total == 0:
        print("At least one of --journalism or --legal must be positive.", file=sys.stderr)
        return 1

    gen_script = REPO_ROOT / "scripts" / "benchmark_data" / "generate_vertical_corpora.py"
    export_script = REPO_ROOT / "scripts" / "export_for_ml.py"
    if not gen_script.is_file() or not export_script.is_file():
        print("Generator or export script not found.", file=sys.stderr)
        return 1

    env = {**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)}

    with tempfile.TemporaryDirectory(prefix="chronicle_synthetic_") as tmp:
        tmp_path = Path(tmp)
        corpora_dir = tmp_path / "corpora"
        corpora_dir.mkdir()
        j_dir = corpora_dir / "journalism"
        l_dir = corpora_dir / "legal"
        j_dir.mkdir()
        l_dir.mkdir()

        # Step 1: generate .chronicle files
        cmd_gen = [
            sys.executable,
            str(gen_script),
            "--journalism",
            str(args.journalism),
            "--legal",
            str(args.legal),
            "--output",
            str(corpora_dir),
        ]
        r = subprocess.run(cmd_gen, cwd=str(REPO_ROOT), env=env)
        if r.returncode != 0:
            print("Generator failed.", file=sys.stderr)
            return r.returncode

        # Step 2: import all into one project
        project_path = Path(args.project) if args.project else tmp_path / "project"
        if not args.project:
            project_path.mkdir()

        from chronicle.store.export_import import import_investigation

        project_path.mkdir(parents=True, exist_ok=True)
        chronicle_files = list(j_dir.glob("*.chronicle")) + list(l_dir.glob("*.chronicle"))
        for i, cf in enumerate(chronicle_files):
            import_investigation(cf, project_path)
            if (i + 1) % 200 == 0:
                print(f"Imported {i + 1}/{len(chronicle_files)} .chronicle files...", file=sys.stderr)

        # Step 3: export to JSONL
        args.output.parent.mkdir(parents=True, exist_ok=True)
        cmd_export = [
            sys.executable,
            str(export_script),
            "--project",
            str(project_path),
            "--output",
            str(args.output.resolve()),
        ]
        r = subprocess.run(cmd_export, cwd=str(REPO_ROOT), env=env)
        if r.returncode != 0:
            print("Export for ML failed.", file=sys.stderr)
            return r.returncode

        if args.project:
            print(f"Project kept at {project_path}", file=sys.stderr)
        # else temp dir (and project) are removed on exit

    print(f"Written {args.output} ({total} investigations, one row per claim)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
