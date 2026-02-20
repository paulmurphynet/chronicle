# Chronicle defensibility eval: input/output contract

> **Purpose:** Define the minimal **contract** for a Chronicle-based defensibility evaluation so labs and eval frameworks can plug in without depending on a specific implementation. One evaluation = one (query, answer, evidence) in, one defensibility metrics object (or error) out.

**Companion:** [Defensibility metrics schema](defensibility-metrics-schema.md) (output field semantics), [Using Chronicle in RAG evaluation](eval-and-benchmarking.md) (how to run pipelines and read metrics), [Integrating with Chronicle](integrating-with-chronicle.md) (minimum integration). **Machine-readable:** [eval_contract_schema.json](eval_contract_schema.json) — JSON Schema for input (`$defs/Input`) and output success/error (`$defs/OutputSuccess`, `$defs/OutputError`) for validation in harnesses.

**Contract version:** 1.0. Breaking changes to the input/output shape will be rare and announced. If you only do one thing: pipe one JSON object (query, answer, evidence) to the scorer stdin and read one JSON object from stdout. See [Current implementations](#3-current-implementations).

---

## Important: what the default scorer does and does not do

**The standalone scorer**, by default, links **every** evidence chunk as **support** for the single claim (the answer). It does **not** validate that each chunk actually supports or entails the answer. So defensibility metrics (e.g. support_count, provenance_quality) reflect this structural convention—not a check that evidence semantically supports the claim. **For higher assurance**, validate or curate evidence–claim links (e.g. by human review or by an NLI/entailment step) and then record them in a full Chronicle session; the default scorer path does not perform that validation.

---

## 1. Input

A single defensibility eval run is defined by:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | The user question or prompt. |
| `answer` | string | Yes | The model's answer (recorded as the claim text). |
| `evidence` | array | Yes | The evidence the answer is based on (e.g. retrieved chunks or documents). See below. |

**Evidence** must be a list. Each item can be:

- A **string** — one chunk of text (e.g. a retrieved passage).
- An **object** with optional `text`, `path`, or `url` — for implementations that support file paths or URLs: `{"text": "..."}` or `{"path": "/path/to/doc.txt"}` or `{"url": "https://..."}`.

Implementations may accept only strings (chunks), paths, or URLs; the contract does not require all formats. The standalone scorer accepts strings and objects with `text`, `path`, or `url` (URLs are fetched with SSRF safeguards).

**Example input (JSON):**

```json
{
  "query": "What was the revenue in Q1 2024?",
  "answer": "Revenue in Q1 2024 was $1.2M.",
  "evidence": [
    "The company reported revenue of $1.2M in Q1 2024.",
    "Growth was driven by enterprise contracts."
  ]
}
```

---

## 2. Output

### 2.1 Success

On success, the evaluator returns a single JSON object with the **defensibility metrics** for the claim derived from (answer, evidence). The shape is stable and defined in [Defensibility metrics schema](defensibility-metrics-schema.md). Eval harnesses can rely on at least:

| Field | Type | Description |
|-------|------|-------------|
| `contract_version` | string (optional) | Contract version, e.g. `"1.0"`. Present in scorer output. |
| `claim_uid` | string | Claim identifier. |
| `provenance_quality` | string | `strong` \| `medium` \| `weak` \| `challenged`. |
| `corroboration` | object | At least `support_count`, `challenge_count`, `independent_sources_count` (ints). |
| `contradiction_status` | string | `none` \| `open` \| `acknowledged` \| `resolved`. |
| `link_assurance_level` | string (optional) | `human_reviewed` \| `tool_generated` \| `mixed_human_tool` \| `unknown` \| `no_links`. Helps interpret support/challenge counts. |
| `link_assurance_caveat` | string (optional) | Human-readable caveat about link provenance (e.g. tool-generated links still need review for high-assurance uses). |
| `knowability` | object (optional) | When present: `known_as_of`, `known_range_start`, `known_range_end`, `knowable_from`, `temporal_confidence` (0..1). |

**Example output (success):**

```json
{
  "contract_version": "1.0",
  "claim_uid": "claim_abc123",
  "provenance_quality": "medium",
  "corroboration": {
    "support_count": 2,
    "challenge_count": 0,
    "independent_sources_count": 1
  },
  "contradiction_status": "none",
  "link_assurance_level": "tool_generated",
  "link_assurance_caveat": "Links were recorded only by tool/system actors; human review is recommended for high-assurance uses."
}
```

### 2.2 Error

On failure, the evaluator returns a JSON object that includes an **`error`** key so harnesses can distinguish from success. Optional context: `claim_uid`, `investigation_uid`, `message`.

| Error | Meaning |
|-------|--------|
| `invalid_input` | Input JSON invalid or missing required fields (query, answer, evidence); or evidence has no usable text chunks. |
| `no_investigation` | No investigation was created (e.g. pipeline or scorer failed before writing). |
| `no_claim` | Investigation exists but no claim was produced for the answer. |
| `no_defensibility_score` | Claim exists but defensibility could not be computed (e.g. no support links). |
| (other) | Implementation-specific (e.g. `langchain_core_required` for the adapter script). |

**Example output (error):**

```json
{
  "contract_version": "1.0",
  "claim_uid": null,
  "error": "no_claim",
  "investigation_uid": "inv_xyz"
}
```

Harnesses should treat any object that contains `"error"` as a failed run and not assume `provenance_quality` or other metrics are present.

---

## 3. Current implementations

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py` accepts input as one JSON object on **stdin** or via **CLI flags** `--query`, `--answer`, `--evidence` (evidence is a JSON array string, e.g. `--evidence '["chunk1","chunk2"]'`). Prints the contract output to stdout. No API server or RAG stack. From repo root: `echo '{"query":"...","answer":"...","evidence":["chunk1","chunk2"]}' | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py` or use the flags. Evidence items can be strings or objects with `"text"`, `"path"` (file path; file content is read as text), or `"url"` (URL is fetched with SSRF safeguards; content used as text). In the standalone scorer, **every evidence chunk is linked as support** for the single claim (the answer); this is a structural convention for evals, not a check that each chunk actually supports the answer (see [Evidence–claim linking](../critical_areas/04-evidence-claim-linking.md)). **Docker:** `docker build -f scripts/Dockerfile.standalone_scorer -t chronicle-scorer .` then `echo '{"query":"...",...}' | docker run -i chronicle-scorer`. See [scripts/README_standalone_scorer.md](../scripts/README_standalone_scorer.md) and [Eval and benchmarking](eval-and-benchmarking.md#3-extract-defensibility-metrics).
- **Eval harness adapter** — `scripts/eval_harness_adapter.py` runs a **built-in** LangChain RAG flow (fixed query, docs, and mock LLM) and prints one JSON object (claim_uid + metrics or error) to stdout. Use it as the hook pattern; replace the chain with your own and keep the "get claim UID, call defensibility_metrics_for_claim, print JSON" logic. See [Eval harness adapter](defensibility-metrics-schema.md#5-eval-harness-adapter-script-and-python-api).
- **Python API** — In your pipeline, after creating an investigation, ingesting evidence, proposing the claim, and linking support, call `chronicle.eval_metrics.defensibility_metrics_for_claim(session, claim_uid)`. It returns the same metrics dict or `None`. See [Using Chronicle in RAG evaluation](eval-and-benchmarking.md#3-extract-defensibility-metrics).
- **HTTP API** — After the same write steps via the API, call `GET /claims/{claim_uid}/defensibility` and use the response (same fields). See [Defensibility metrics schema](defensibility-metrics-schema.md#1-where-the-metrics-come-from).

---

## 4. Machine-readable schema

[eval_contract_schema.json](eval_contract_schema.json) provides a JSON Schema (draft 2020-12) for the contract. Use `$defs/Input` to validate request payloads and `$defs/OutputSuccess` or `$defs/OutputError` to validate scorer output (success and error shapes are disjoint: success has no `error` key).

---

## 5. Summary

| | |
|--|--|
| **Input** | `query` (string), `answer` (string), `evidence` (array of strings or objects with text/path/url). |
| **Output (success)** | One JSON object: `claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, optional `knowability`. |
| **Output (error)** | One JSON object including `error` (e.g. `no_investigation`, `no_claim`, `no_defensibility_score`); optional `claim_uid`, `investigation_uid`, `message`. |

For full field semantics and examples, see [Defensibility metrics schema](defensibility-metrics-schema.md).
