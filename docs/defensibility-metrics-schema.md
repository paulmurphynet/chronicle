# Stable defensibility metrics schema (for eval harnesses)

> **Purpose:** Define the **stable shape** of "defensibility metrics for a claim" so RAG eval harnesses and benchmarking tools can consume defensibility in a consistent way. The same shape is returned by `get_defensibility_score` (session) and `GET /claims/{claim_uid}/defensibility` (API).

**Companion:** [Eval contract (input/output)](eval_contract.md), [Technical report](technical-report.md) (defensibility definition, schema, evaluation), [Benchmark](benchmark.md), [Integrating with Chronicle](integrating-with-chronicle.md).

---

## 1. Where the metrics come from

- **API:** `GET /claims/{claim_uid}/defensibility` — returns a JSON object that includes the scorecard fields below plus `explanations` and `sources_backing_claim`. Optional query `use_strength_weighting=true` uses strength-weighted corroboration; default is count-based.
- **Session (in-process):** `session.get_defensibility_score(claim_uid)` returns a `DefensibilityScorecard`; convert to dict (e.g. `dataclasses.asdict`) for the same shape. Optional `use_strength_weighting=True` for strength-weighted corroboration.
- **Batch (investigation):** `GET /investigations/{investigation_uid}/defensibility` returns per-claim scorecards in the same shape.

---

## 2. Canonical metrics fields (stable subset)

Eval harnesses can rely on the following fields. All are present in the API response and in the serialized scorecard.

| Field | Type | Description |
|-------|------|-------------|
| `claim_uid` | string | Claim identifier. |
| `provenance_quality` | string | `strong` \| `medium` \| `weak` \| `challenged`. Primary summary for "how defensible is this claim?" |
| `corroboration` | object | At least: `support_count` (int), `challenge_count` (int), `independent_sources_count` (int). Optional when strength weighting used: `support_weighted_sum`, `challenge_weighted_sum` (float). |
| `corroboration.support_count` | int | Number of support links. |
| `corroboration.challenge_count` | int | Number of challenge links. |
| `corroboration.independent_sources_count` | int | Count of distinct sources (as linked by the user) backing support; not independently verified. In the **standalone scorer** path, evidence is not linked to sources, so this is typically 0. |
| `contradiction_status` | string | `none` \| `open` \| `acknowledged` \| `resolved`. |
| `knowability` | object (optional) | When set: `known_as_of` (ISO8601 or null), `knowable_from` (string or null). "When could we first defend this claim?" |

**sources_backing_claim** (optional): when present, list of sources backing the claim, each with `source_uid`, `display_name`, and optional `independence_notes` / `reliability_notes` (user-supplied; we record, we don't verify). Support/challenge links may include optional **rationale** (warrant) and **defeater_kind** (e.g. rebutting, undercutting on challenges); we record, we don't verify.

Additional fields in the full scorecard (temporal_validity, attribution_posture, decomposition_precision, contradiction_handling, evidence_integrity, evidence_trust, risk_signals, weakest_link) are stable but not required for a minimal eval metrics subset.

---

## 3. As-of and point-in-time metrics

For "defensibility as of event E or timestamp T" (e.g. for audits or time-series evals):

- **API:** `GET /investigations/{investigation_uid}/defensibility-as-of?as_of=ISO8601` or `?as_of_event_id=...` returns per-claim defensibility at that point. Each claim entry has the same metrics shape; the response also includes `as_of` (the label used).
- **Audit export:** `GET /investigations/{investigation_uid}/audit-export?as_of_date=...` or `?as_of_event_id=...` includes `defensibility_snapshot` (per claim: provenance_quality, contradiction_status, corroboration) and `defensibility_as_of`.

---

## 4. Example (minimal extract for evals)

```json
{
  "claim_uid": "claim_abc123",
  "provenance_quality": "medium",
  "corroboration": {
    "support_count": 2,
    "challenge_count": 0,
    "independent_sources_count": 1
  },
  "contradiction_status": "none",
  "knowability": {
    "known_as_of": "2024-01-15",
    "knowable_from": null
  }
}
```

Eval harnesses can read these fields from the full `GET /claims/{claim_uid}/defensibility` response (or from the batch endpoint) and ignore extra keys. The API and `get_defensibility_score` return this shape consistently so you can compare runs or configs by claim_uid and metrics.

---

## 5. Eval harness adapter (script and Python API)

A thin **eval harness adapter** (step D.2) runs a RAG pipeline with a Chronicle integration, reads the resulting claim UID and defensibility score, and outputs a single JSON object with `claim_uid` and the metrics above. This is the hook for RAG eval frameworks to record defensibility per run.

- **Script:** `scripts/eval_harness_adapter.py` — runs one LangChain RAG flow with the Chronicle callback handler and prints the metrics JSON to stdout. From repo root: `PYTHONPATH=. python3 scripts/eval_harness_adapter.py`.
- **Python API:** `chronicle.eval_metrics.defensibility_metrics_for_claim(session, claim_uid)` returns the same metrics dict (or `None` if no scorecard). Use this inside a custom pipeline or as a callback after each RAG run. `chronicle.eval_metrics.scorecard_to_metrics_dict(claim_uid, scorecard)` builds the dict from an existing `DefensibilityScorecard`.
