from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

bundle_module = import_module("scripts.whitepaper.build_submission_bundles")


def test_build_submission_bundles(tmp_path: Path) -> None:
    rc = bundle_module.main(
        [
            "--revision",
            "test-v0",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0

    base = tmp_path / "test-v0"
    manifest_path = base / "submission_bundle_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["revision"] == "test-v0"
    assert len(manifest["bundles"]) == 3

    for item in manifest["bundles"]:
        bundle_dir = Path(item["bundle_dir"])
        bundle_zip = Path(item["bundle_zip"])
        assert bundle_dir.is_dir()
        assert bundle_zip.is_file()
        assert (bundle_dir / "bundle_manifest.json").is_file()
        assert (bundle_dir / "checksums.sha256").is_file()
