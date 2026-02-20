#!/usr/bin/env python3
"""Build venue-specific standards submission bundles for a whitepaper revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _copy(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _write_checksums(bundle_dir: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        if path.name in {"checksums.sha256", "bundle_manifest.json"}:
            continue
        rel = path.relative_to(bundle_dir)
        entries.append({"path": str(rel), "sha256": _sha256(path)})
    lines = [f"{item['sha256']}  {item['path']}" for item in entries]
    (bundle_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


def _zip_dir(src: Path, dst_zip: Path) -> None:
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            arcname = path.relative_to(src)
            zf.write(path, arcname)


def _build_evidence_pack(out_dir: Path) -> Path:
    from scripts.whitepaper import build_evidence_pack as pack_module

    rc = pack_module.main(
        [
            "--components",
            "standards",
            "verifier",
            "--output-dir",
            str(out_dir),
        ]
    )
    if rc != 0:
        raise RuntimeError(f"evidence-pack build failed with status {rc}")
    manifest = out_dir / "evidence_pack_manifest.json"
    if not manifest.is_file():
        raise RuntimeError(f"missing evidence pack manifest: {manifest}")
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="v0.3", help="Whitepaper revision label")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/standards_submissions"),
        help="Base output directory for submission bundles",
    )
    parser.add_argument(
        "--skip-evidence-pack",
        action="store_true",
        help="Reuse existing evidence pack folder if present",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    generated_at = datetime.now(UTC).isoformat()
    base_dir = (REPO_ROOT / args.output_dir / args.revision).resolve()
    bundles_dir = base_dir / "bundles"
    evidence_dir = base_dir / "evidence_pack"
    base_dir.mkdir(parents=True, exist_ok=True)
    bundles_dir.mkdir(parents=True, exist_ok=True)

    required_docs = [
        "docs/whitepaper-draft.md",
        "docs/whitepaper-citation.md",
        "docs/whitepaper-publication-metadata.json",
        "docs/whitepaper-evidence-pack.md",
        "docs/standards-profile.md",
        "docs/standards-submission-package.md",
        "docs/adjacent-standards-guidance.md",
        "docs/adr/0003-standards-interoperability-profile.md",
        "docs/to_do.md",
    ]

    missing = [path for path in required_docs if not (REPO_ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"missing required docs: {missing}")

    if args.skip_evidence_pack and (evidence_dir / "evidence_pack_manifest.json").is_file():
        evidence_manifest = evidence_dir / "evidence_pack_manifest.json"
    else:
        if evidence_dir.exists():
            shutil.rmtree(evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_manifest = _build_evidence_pack(evidence_dir)

    venues = {
        "w3c_linked_data": {
            "title": "W3C-linked JSON-LD/PROV/VC review bundle",
            "focus": "Mapping semantics, compatibility language, and trust-boundary precision.",
        },
        "c2pa_ecosystem": {
            "title": "C2PA ecosystem review bundle",
            "focus": "C2PA compatibility path and metadata-only verification semantics.",
        },
        "applied_research": {
            "title": "Applied research reproducibility review bundle",
            "focus": "Reproducibility, defensibility metrics reporting, and verifier-backed evidence chain.",
        },
    }

    top_manifest: dict[str, Any] = {
        "schema_version": 1,
        "revision": args.revision,
        "generated_at": generated_at,
        "base_dir": str(base_dir),
        "evidence_pack_manifest": str(evidence_manifest),
        "bundles": [],
    }

    for venue_key, venue in venues.items():
        venue_dir = bundles_dir / venue_key
        if venue_dir.exists():
            shutil.rmtree(venue_dir)
        venue_dir.mkdir(parents=True, exist_ok=True)

        copied_paths: list[str] = []
        for rel in required_docs:
            src = REPO_ROOT / rel
            dst = venue_dir / rel
            _copy(src, dst)
            copied_paths.append(rel)

        for rel in [
            "evidence_pack_manifest.json",
            "standards_profiles/standards_jsonld_export.json",
            "standards_profiles/standards_jsonld_validation.json",
            "standards_profiles/claimreview_export.json",
            "standards_profiles/ro_crate_export.json",
            "standards_profiles/c2pa_export_disabled.json",
            "standards_profiles/c2pa_export_metadata_only.json",
            "standards_profiles/vc_export_disabled.json",
            "standards_profiles/vc_export_metadata_only.json",
            "standards_profiles/sample_investigation.chronicle",
            "verifier/verification_report.json",
        ]:
            src = evidence_dir / rel
            if src.is_file():
                dst = venue_dir / "evidence_pack" / rel
                _copy(src, dst)
                copied_paths.append(str(Path("evidence_pack") / rel))

        cover_path = venue_dir / "README.md"
        cover_path.write_text(
            "\n".join(
                [
                    f"# {venue['title']}",
                    "",
                    f"Revision: `{args.revision}`",
                    f"Generated at: `{generated_at}`",
                    "",
                    "## Focus",
                    venue["focus"],
                    "",
                    "## Requested feedback",
                    "1. Mapping correctness and terminology precision.",
                    "2. Guarantee boundary clarity (semantic vs cryptographic claims).",
                    "3. Practical interoperability concerns for this ecosystem.",
                    "",
                    "## Key entry points",
                    "- `docs/whitepaper-draft.md`",
                    "- `docs/standards-profile.md`",
                    "- `docs/standards-submission-package.md`",
                    "- `evidence_pack/evidence_pack_manifest.json`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        checksums = _write_checksums(venue_dir)
        bundle_manifest = {
            "schema_version": 1,
            "revision": args.revision,
            "venue": venue_key,
            "title": venue["title"],
            "generated_at": generated_at,
            "files": checksums,
        }
        _write_json(venue_dir / "bundle_manifest.json", bundle_manifest)
        zip_path = bundles_dir / f"{venue_key}_{args.revision}.zip"
        _zip_dir(venue_dir, zip_path)

        top_manifest["bundles"].append(
            {
                "venue": venue_key,
                "title": venue["title"],
                "bundle_dir": str(venue_dir),
                "bundle_zip": str(zip_path),
                "file_count": len(checksums),
            }
        )

    _write_json(base_dir / "submission_bundle_manifest.json", top_manifest)
    print(f"Wrote submission bundles: {base_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
