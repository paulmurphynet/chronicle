from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pack_module = import_module("scripts.whitepaper.build_evidence_pack")


def test_whitepaper_pack_standards_and_verifier(tmp_path: Path) -> None:
    out_dir = tmp_path / "pack"
    rc = pack_module.main(
        [
            "--output-dir",
            str(out_dir),
            "--components",
            "standards",
            "verifier",
        ]
    )
    assert rc == 0

    manifest_path = out_dir / "evidence_pack_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["summary"]["failed"] == 0
    names = {item["name"] for item in manifest["components"]}
    assert names == {"standards", "verifier"}

    standards_export = out_dir / "standards_profiles" / "standards_jsonld_export.json"
    vc_export = out_dir / "standards_profiles" / "vc_export_metadata_only.json"
    verifier_report = out_dir / "verifier" / "verification_report.json"
    assert standards_export.is_file()
    assert vc_export.is_file()
    assert verifier_report.is_file()

    vc_payload = json.loads(vc_export.read_text(encoding="utf-8"))
    assert vc_payload["verification"]["mode"] == "metadata_only"
    assert isinstance(vc_payload["attestations"]["claims"], list)

    verify_payload = json.loads(verifier_report.read_text(encoding="utf-8"))
    assert verify_payload["verified"] is True
    assert len(verify_payload["checks"]) > 0


def test_whitepaper_pack_benchmark_component(tmp_path: Path) -> None:
    out_dir = tmp_path / "pack"
    rc = pack_module.main(
        [
            "--output-dir",
            str(out_dir),
            "--components",
            "benchmark",
        ]
    )
    assert rc == 0

    results_path = out_dir / "benchmark" / "benchmark_defensibility_results.json"
    trust_path = out_dir / "benchmark" / "trust_progress_report.json"
    manifest_path = out_dir / "evidence_pack_manifest.json"

    assert results_path.is_file()
    assert trust_path.is_file()
    assert manifest_path.is_file()

    results_payload = json.loads(results_path.read_text(encoding="utf-8"))
    trust_payload = json.loads(trust_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert results_payload["benchmark"] == "run_defensibility_benchmark"
    assert "summary" in trust_payload
    assert manifest["summary"]["failed"] == 0
