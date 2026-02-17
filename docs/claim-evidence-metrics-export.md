# Claim–evidence–metrics export (for fact-checking UIs and dashboards)

This doc defines a **stable JSON shape** for “one claim + evidence references + support/challenge counts + defensibility metrics” so fact-checking UIs, dashboards, or pipelines can ingest Chronicle data without depending on the full .chronicle or generic export layout.

**Related:** [Generic export](GENERIC_EXPORT.md) (full investigation JSON/CSV), [Defensibility metrics schema](defensibility-metrics-schema.md) (field semantics), [Eval contract](eval_contract.md) (scorer I/O).

---

## 1. Intended consumers

- **Fact-checking UIs** — Show a claim with its supporting/challenging evidence refs and a defensibility score.
- **Dashboards** — Per-claim rows with evidence counts and provenance_quality.
- **Pipelines** — Ingest “claim + evidence refs + metrics” from Chronicle (or from an adapter that emits this shape).

Consumers can treat this as the **canonical slice** for “one claim and its defensibility context.”

---

## 2. Per-claim export shape (stable)

Each item in the export is one claim with evidence references and defensibility. Schema version: **1**.

| Field | Type | Description |
|-------|------|-------------|
| `claim_uid` | string | Chronicle claim ID. |
| `claim_text` | string | The claim statement. |
| `investigation_uid` | string | Parent investigation. |
| `evidence_refs` | array | List of evidence references (see below). |
| `support_count` | int | Number of support links (spans → this claim). |
| `challenge_count` | int | Number of challenge links. |
| `defensibility` | object | Defensibility scorecard (see [Defensibility metrics schema](defensibility-metrics-schema.md)). At least: `provenance_quality`, `corroboration`, `contradiction_status`. |

**evidence_refs** entry:

| Field | Type | Description |
|-------|------|-------------|
| `evidence_uid` | string | Chronicle evidence item ID. |
| `span_uid` | string (optional) | Span ID if the link is span-level. |
| `link_type` | string | `SUPPORT` or `CHALLENGE`. |
| `uri` | string (optional) | Evidence item URI (e.g. path in .chronicle). |

You can derive this from the read model: for a claim, list evidence_link rows (span_uid, link_type), join to evidence_span and evidence_item for uri and evidence_uid, then attach `get_defensibility_score(claim_uid)` for the defensibility object.

---

## 3. Wrapper format (investigation-level)

A full export for one investigation can be a single JSON object:

```json
{
  "schema_version": 1,
  "schema_doc": "https://github.com/chronicle/Chronicle/docs/claim-evidence-metrics-export.md",
  "investigation_uid": "inv_...",
  "claims": [
    {
      "claim_uid": "claim_...",
      "claim_text": "Revenue was $1.2M in Q1 2024.",
      "investigation_uid": "inv_...",
      "evidence_refs": [
        { "evidence_uid": "ev_...", "span_uid": "span_...", "link_type": "SUPPORT", "uri": "evidence/ev_....txt" }
      ],
      "support_count": 1,
      "challenge_count": 0,
      "defensibility": {
        "claim_uid": "claim_...",
        "provenance_quality": "strong",
        "corroboration": { "support_count": 1, "challenge_count": 0, "independent_sources_count": 1 },
        "contradiction_status": "none"
      }
    }
  ]
}
```

This is a **thin wrapper**: you build it from the same data as [generic export](GENERIC_EXPORT.md) plus evidence_link and `get_defensibility_score`. The repo does not yet provide a single API that returns exactly this wrapper; you can assemble it from `build_generic_export_json`, the read model’s evidence_link listing, and defensibility scorecards. A future helper (e.g. `build_claim_evidence_metrics_export`) could standardize it in code.

---

## 4. Consumers can ingest this

- **Fact-checking UIs:** Use `claim_uid`, `claim_text`, `evidence_refs`, and `defensibility.provenance_quality` (and optionally `defensibility.contradiction_status`) to render a card or row. Resolve evidence content from the project or .chronicle by `uri` / `evidence_uid`.
- **Dashboards:** Aggregate by `provenance_quality`, `support_count`, `challenge_count`; filter by `investigation_uid`.
- **Adapters out:** Any adapter that exports “Chronicle → fact-checking format” should emit at least claim + evidence refs + support/challenge counts + defensibility; this doc is the reference shape.
