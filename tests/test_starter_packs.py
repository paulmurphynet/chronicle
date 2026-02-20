from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

starter_module = import_module("scripts.starter_packs.bootstrap")


@pytest.mark.parametrize("pack", ["journalism", "legal", "audit"])
def test_starter_pack_bootstrap_generates_defensible_artifacts(tmp_path: Path, pack: str) -> None:
    project_path = tmp_path / f"{pack}_project"
    output_dir = tmp_path / f"{pack}_artifacts"

    rc = starter_module.main(
        [
            "--pack",
            pack,
            "--path",
            str(project_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert rc == 0

    manifest_path = output_dir / "starter_pack_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "passed"
    assert manifest["pack"] == pack
    assert manifest["summary"]["claims_in_snapshot"] > 0

    review_packet = Path(manifest["artifacts"]["review_packet"])
    audit_export = Path(manifest["artifacts"]["audit_export_bundle"])
    standards_export = Path(manifest["artifacts"]["standards_jsonld_export"])
    claimreview_export = Path(manifest["artifacts"]["claimreview_export"])
    ro_crate_export = Path(manifest["artifacts"]["ro_crate_export"])

    assert review_packet.is_file()
    assert audit_export.is_file()
    assert standards_export.is_file()
    assert claimreview_export.is_file()
    assert ro_crate_export.is_file()
