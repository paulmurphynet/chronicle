# Lesson 07: Integrations and scripts

Objectives: You’ll know where RAG and framework integrations live, what the main scripts and protocol adapters do (benchmark, eval harness adapter, starter packs, API ingestion pipeline, integration contract harnesses, MCP server), and how they plug into the Chronicle session.

**Key files:**

- [chronicle/integrations/](../chronicle/integrations/) — LangChain, LlamaIndex, Haystack (when present)
- [scripts/README.md](../scripts/README.md) — script layout, first-class scripts table, and quick runs
- [scripts/adapters/](../scripts/adapters/) — RAG→scorer example, fact-checker→Chronicle, provenance→Chronicle
- [chronicle/api/app.py](../chronicle/api/app.py) — optional HTTP API (install `.[api]`)
- [scripts/standalone_defensibility_scorer.py](../scripts/standalone_defensibility_scorer.py) — already covered in Lesson 02
- [scripts/starter_packs/bootstrap.py](../scripts/starter_packs/bootstrap.py) — opinionated vertical starter packs (journalism, legal, audit)
- [scripts/api_ingestion_pipeline_example.py](../scripts/api_ingestion_pipeline_example.py) — batch input → API writes → defensibility + export artifacts
- [scripts/check_integration_export_contracts.py](../scripts/check_integration_export_contracts.py) — JSON/CSV/Markdown/signed-bundle end-to-end contract harness
- [docs/eval-and-benchmarking.md](../docs/eval-and-benchmarking.md) — how to run pipelines and report defensibility
- [docs/api.md](../docs/api.md) — HTTP API config and endpoints
- [docs/rag-evals-defensibility-metric.md](../docs/rag-evals-defensibility-metric.md) — RAG evals: contract and scorer in your harness
- [docs/starter-packs.md](../docs/starter-packs.md) — vertical onboarding packs and expected artifacts
- [docs/api-ingestion-pipeline-example.md](../docs/api-ingestion-pipeline-example.md) — deterministic API pipeline walkthrough
- [docs/integration-export-hardening.md](../docs/integration-export-hardening.md) — hardened interoperability contract for export/import surfaces
- [docs/case-study-lizzie-borden.md](../docs/case-study-lizzie-borden.md) — professional framing for the transcript benchmark dataset
- [docs/mcp.md](../docs/mcp.md) — MCP server integration for agent tool-calling
- [chronicle/mcp/](../chronicle/mcp/) — MCP server/service implementation

---

## Integrations

The chronicle/integrations/ directory (or package) is intended to hold handlers or callbacks so that RAG frameworks (LangChain, LlamaIndex, Haystack) can write evidence and claims into Chronicle during a run. For example:

- A LangChain callback might create an investigation, ingest retrieved documents as evidence, and when the chain produces an answer, propose it as a claim and link the retrieved chunks as support.
- The session API is the same; the integration just wires framework events (e.g. “on_retriever_end”, “on_llm_end”) to ChronicleSession methods.

If the repo has `chronicle/integrations/langchain.py` or similar, open it and see how it uses create_investigation, ingest_evidence, propose_claim, link_support. If the directory is empty or minimal, the pattern is still: framework event → session method. Demos may live in scripts/ (e.g. `langchain_rag_chronicle.py`, `cross_framework_rag_chronicle.py`).

## First-class scripts

Open scripts/README.md and find the “First-class scripts” table. These are the main entry points for pipelines and interop:

- **chronicle quickstart-rag** — One-command RAG flow (temp project, investigation, ingest, claim, link, defensibility). See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md).
- **chronicle-verify** — Verify a .chronicle file (manifest, schema, evidence hashes). Stdlib only.
- **standalone_defensibility_scorer.py** — One (query, answer, evidence) in → defensibility JSON out (Lesson 02).
- **benchmark_data/run_defensibility_benchmark.py** — Fixed queries, defensibility per answer (`--mode session` recommended for reproducible local runs).
- **eval_harness_adapter.py** — Adapt a RAG run to the eval contract and record defensibility.
- **run_reference_workflows.py** — One-command execution of journalism + benchmark + compliance + Neo4j checks with a consolidated report.
- **starter_packs/bootstrap.py** — Create a clean workspace from opinionated vertical defaults (journalism/legal/audit), including deterministic fixture import and report/export artifacts.
- **api_ingestion_pipeline_example.py** — Run an end-to-end API write/read/export flow from one batch input.
- **check_integration_export_contracts.py** — Validate adapter/API-facing import/export contracts for JSON, CSV ZIP, Markdown reasoning brief, `.chronicle`, and signed bundle flows.
- **chronicle-mcp** — Run Chronicle as an MCP server so AI assistants can execute Chronicle investigation/evidence/claim/defensibility/export tools.
- **export_for_ml.py** — Export investigation data for ML/training.
- **rag_path_demo.py** — Minimal RAG path (session: ingest, claim, link).
- **\*_rag_chronicle.py** — LangChain, LlamaIndex, Haystack, cross-framework demos.

Use this table when you need to plug Chronicle into an eval harness, benchmark, or export pipeline.

## Adapters (scripts/adapters/)

Open scripts/adapters/README.md. Adapters map external formats into Chronicle (or into the scorer):

- **example_rag_to_scorer.py** — Minimal copy-paste template: read JSON (query, answer, evidence) from stdin or file, call the scorer, print metrics.
- **starter_batch_to_scorer.py** — Batch-ready template: JSONL harness rows in, scored JSONL rows out; supports mapping profiles for nested key paths.
- **ragas_batch_to_chronicle.py** — RAGAS-first adapter: auto-maps common RAGAS fields (`question`, `answer`, `contexts` / `retrieved_contexts`) to Chronicle eval contract rows and emits scored JSONL.
- **validate_adapter_outputs.py** — Validates adapter output rows against the eval contract shape (success/error payload).
- **fact_checker_to_chronicle.py** — Fact-checker output (claim + verdict + sources) → evidence items, propose_claim, support/challenge links. Expected JSON: `claim`, `verdict`, `sources` (with snippet, stance).
- **provenance_to_chronicle.py** — Provenance assertions (“this evidence from this source”) → register_source, ingest_evidence, link_evidence_to_source. We record; we don’t verify. Requires `--path` to a project.

These are templates: you can copy and adjust for your fact-checking or provenance pipeline. See [docs/provenance-recording.md](../docs/provenance-recording.md) and [docs/external-ids.md](../docs/external-ids.md).

## Optional HTTP API

If you install the `[api]` extra (`pip install -e ".[api]"`), you get a minimal HTTP API in chronicle/api/app.py. Run it with:

```bash
export CHRONICLE_PROJECT_PATH=/path/to/project
uvicorn chronicle.api.app:app --reload
```

It exposes write (investigations, evidence, claims, links, tensions), read (claim, defensibility, reasoning brief), and export/import (.chronicle). Response shapes match the eval contract and defensibility schema. No auth in this minimal version; see [docs/api.md](../docs/api.md). Useful for fact-checking or provenance UIs that call Chronicle over HTTP.

## Optional MCP server

If you install the `[mcp]` extra (`pip install -e ".[mcp]"`), you can expose Chronicle tools to MCP-capable assistants:

```bash
chronicle-mcp --project-path /path/to/project
```

This is usually paired with local `stdio` transport for agent integrations. Chronicle MCP tools mirror session operations (create investigation, ingest evidence text, propose claim, link support/challenge, get defensibility/reasoning brief, export). See [docs/mcp.md](../docs/mcp.md).

## Other scripts (layout)

Beyond the first-class list, scripts/README.md also describes:

- **generate_sample_chronicle.py** — Produces a sample .chronicle (verticals, e.g. journalism).
- **ingest_transcript_csv.py** — CSV → one evidence item + one span + one claim per row; exports .chronicle.
- **suggest_tensions_with_llm.py** — Suggests tensions (heuristic or Ollama LLM), optionally applies them.
- **ingest_chronicle_to_aura.py** — Verify → import .chronicle into a graph project → sync to Neo4j (Aura pipeline).

All of these use the session (or the verifier, or the Neo4j sync) under the hood.

## Case-study framing (required reading for transcript benchmarks)

If you use `test_data/lb_inquest/inquest.csv`, read [docs/case-study-lizzie-borden.md](../docs/case-study-lizzie-borden.md) first.

Use that dataset as an evidence-quality benchmark, not as a vehicle for case adjudication:

1. Keep language neutral and professional.
2. Treat transcript statements as claims requiring support/challenge structure.
3. Evaluate whether Chronicle improves citation quality and temporal consistency relative to baseline LLM answers.

## How scripts use the session

Typical pattern:

1. Create or open a project (`create_project` or open existing path).
2. **ChronicleSession(project_path)** — get a session.
3. session.create_investigation(...) then session.ingest_evidence(...), session.propose_claim(...), session.link_support(...) (and optionally session.declare_tension(...)).
4. session.get_defensibility_score(claim_uid) or session.export_investigation(inv_uid, path) or chronicle neo4j-sync --path project.

So scripts are thin orchestration; the engine is the store and commands.

## Try it

1. Run chronicle quickstart-rag from the repo root (with venv activated). Confirm you see defensibility output. See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md) for options (`--path`, `--text`).
2. List the contents of scripts/ and scripts/adapters/. Match the first-class scripts in scripts/README.md to their paths.
3. Open scripts/adapters/example_rag_to_scorer.py and see how it reads JSON and calls the scorer logic. Run it with a one-line JSON input (query, answer, evidence) from stdin.
4. Run `PYTHONPATH=. python3 scripts/adapters/check_examples.py` and verify adapter examples + validation flow pass.
5. Create a small RAGAS-style JSONL (`question`, `answer`, `contexts`) and run `PYTHONPATH=. python3 scripts/adapters/ragas_batch_to_chronicle.py --input runs_ragas.jsonl --output scored_ragas.jsonl`, then validate with `PYTHONPATH=. python3 scripts/adapters/validate_adapter_outputs.py --input scored_ragas.jsonl`.
6. Run `PYTHONPATH=. python3 scripts/check_integration_export_contracts.py --project-path /tmp/chronicle_lesson7_contract_project --output-dir /tmp/chronicle_lesson7_contract_out` and inspect the generated contract report/artifacts.
7. (Optional) Install `.[api]`, set CHRONICLE_PROJECT_PATH, run uvicorn chronicle.api.app:app, and open http://127.0.0.1:8000/docs to try the API.
8. Open scripts/ingest_transcript_csv.py and find where it calls session.ingest_evidence, session.propose_claim, and session.link_support. Confirm it follows the same pattern as the scorer (without the temp project).
9. Read [docs/case-study-lizzie-borden.md](../docs/case-study-lizzie-borden.md) and note the two non-goals: no sensational framing and no claim to establish legal truth.
9. (Optional) Install `.[mcp]`, run `chronicle-mcp --project-path /tmp/chronicle_lesson7_mcp`, and from an MCP client call create-investigation and ingest-evidence-text once.

## Summary

- First-class scripts and CLI (scripts/README.md, CLI): chronicle quickstart-rag for a one-command RAG flow; scorer, verifier, benchmark, eval harness adapter, export_for_ml, RAG demos. Use them to plug Chronicle into pipelines.
- **Onboarding and contract harnesses**: starter packs reduce first-project ambiguity; API ingestion and integration export contract scripts provide deterministic interoperability baselines.
- Adapters (scripts/adapters/): RAG→scorer example, fact-checker→Chronicle, provenance→Chronicle. Copy-paste templates for interop.
- MCP server (`chronicle-mcp`, `chronicle/mcp/`) is the assistant protocol surface for the same Chronicle session operations.
- Optional HTTP API (chronicle/api/, install `.[api]`): write/read/export over HTTP; same shapes as eval contract and defensibility schema.
- Integrations (chronicle/integrations/) wire RAG frameworks to ChronicleSession so that runs record evidence and claims.
- All rely on the same session API and event store; they differ only in input source and output (JSON, .chronicle, Neo4j).

← Previous: [Lesson 06: Defensibility metrics](06-defensibility-metrics.md) | Index: [Lessons](README.md) | Next →: [Lesson 08: The CLI](08-cli.md)

Quiz: [quizzes/quiz-07-integrations-and-scripts.md](quizzes/quiz-07-integrations-and-scripts.md)
