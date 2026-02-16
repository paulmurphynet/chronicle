"""
Generate frontend/public/sample.chronicle for one-click "Try sample".
Delegates to the Journalism vertical generator so there is a single canonical implementation.
Run from repository root: PYTHONPATH=. python3 scripts/generate_sample_chronicle.py
"""

import runpy
from pathlib import Path

# Run the journalism vertical generator (same repo root)
_SCRIPT = Path(__file__).resolve().parent / "verticals" / "journalism" / "generate_sample.py"


def main() -> None:
    runpy.run_path(str(_SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
