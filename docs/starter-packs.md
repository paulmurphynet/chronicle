# Starter packs (Journalism, Legal, Audit)

Opinionated starter packs reduce first-project ambiguity by giving you:

1. A policy-profile default
2. A deterministic fixture import
3. Defensibility-ready report/export artifacts

## Bootstrap command

From repo root:

```bash
PYTHONPATH=. python3 scripts/starter_packs/bootstrap.py \
  --pack journalism \
  --path /tmp/chronicle_journalism
```

Replace `journalism` with `legal` or `audit`.

## What each pack applies

| Pack | Policy profile default | Fixture generator |
|------|------------------------|-------------------|
| `journalism` | `docs/policy-profiles/journalism.json` | `scripts/verticals/journalism/generate_sample.py` |
| `legal` | `docs/policy-profiles/legal.json` | `scripts/verticals/legal/generate_sample.py` |
| `audit` | `docs/policy-profiles/compliance.json` | `scripts/verticals/compliance/generate_sample.py` |

## Generated artifacts

For each pack run, Chronicle writes:

- `starter_pack_manifest.json`
- `fixtures/sample_<pack>.chronicle`
- `reports/review_packet.json`
- `reports/audit_export_bundle.json`
- `exports/standards_jsonld_export.json`
- `exports/claimreview_export.json`
- `exports/ro_crate_export.json`

Default output location:

- `<project_path>/starter_pack_artifacts/<pack>/`

Use `--output-dir` to override.

## Example walkthroughs

Journalism:

```bash
PYTHONPATH=. python3 scripts/starter_packs/bootstrap.py \
  --pack journalism \
  --path ./starter_journalism
```

Legal:

```bash
PYTHONPATH=. python3 scripts/starter_packs/bootstrap.py \
  --pack legal \
  --path ./starter_legal
```

Audit:

```bash
PYTHONPATH=. python3 scripts/starter_packs/bootstrap.py \
  --pack audit \
  --path ./starter_audit
```

## Acceptance proof (clean workspace)

The acceptance tests create clean temp projects and verify each pack produces defensibility-ready artifacts:

```bash
PYTHONPATH=. python3 -m pytest tests/test_starter_packs.py -q
```
