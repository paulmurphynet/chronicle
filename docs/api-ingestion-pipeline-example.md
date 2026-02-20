# API ingestion pipeline example

This example demonstrates an end-to-end API ingestion flow:

1. Batch input payload
2. Investigation creation
3. Evidence ingest + support/challenge linking
4. Claim defensibility readout
5. Review packet and `.chronicle` export artifacts

## Run command

From repo root:

```bash
PYTHONPATH=. python3 scripts/api_ingestion_pipeline_example.py \
  --project-path /tmp/chronicle_api \
  --output-dir /tmp/chronicle_api_out
```

## What it generates

- `api_ingestion_pipeline_report.json`
- `defensibility.json`
- `review_packet.json`
- `reasoning_brief.json`
- `api_ingestion_export.chronicle`

## Optional custom batch input

Pass a JSON payload with:

```json
{
  "title": "Investigation title",
  "claim": "Primary claim text",
  "records": [
    {
      "text": "Evidence body",
      "stance": "support",
      "rationale": "Why this supports/challenges",
      "filename": "evidence.txt"
    }
  ]
}
```

Run with:

```bash
PYTHONPATH=. python3 scripts/api_ingestion_pipeline_example.py \
  --project-path /tmp/chronicle_api \
  --output-dir /tmp/chronicle_api_out \
  --input ./batch_input.json
```

## Regression coverage

Acceptance test:

```bash
PYTHONPATH=. python3 -m pytest tests/test_api_ingestion_pipeline_example.py -q
```
