# Chronicle: Project review

A full review of the repository—strengths, weaknesses, and recommended new or improved features. Use this to prioritize work and communicate project health to stakeholders.

---

## Completion status (review-driven improvements)

| # | Recommendation | Status | Notes |
|---|----------------|--------|--------|
| 1 | Align CI: cov-fail-under=50; do **not** re-enable triggers | Done | [ci.yml](../.github/workflows/ci.yml) uses 50; triggers still disabled. To enable later: uncomment push/PR in ci.yml. |
| 2 | Raise coverage toward 75%; phase 5 in to_do; add tests | Done | Phase 5 step in [to_do](to_do.md); new tests in tests/; fail_under can be raised stepwise. |
| 3 | User manual skeleton under docs/manual/ | Done | [docs/manual/](manual/README.md) with README + chapter stubs. |
| 4 | One-line benchmark in README/getting-started | Done | [Getting started](getting-started.md) and [README](../README.md) have benchmark one-liner. |
| 5 | Integration quick reference | Done | [integration-quick-reference.md](integration-quick-reference.md). |
| 6 | Release checklist in CONTRIBUTING | Done | [CONTRIBUTING](../CONTRIBUTING.md) "Changelog and releases" expanded. |
| 7 | API and Neo4j one line in README | Done | "What's in this repo" mentions optional API and Neo4j. |
| 8 | Coverage report as CI artifact | Done | CI uploads coverage XML + HTML when run. |
| 9 | Stale link check in CI | Done | CI runs check_doc_links.py when workflow runs. |
| — | Re-enable CI on push/PR | **Skipped** | Per maintainer: do not enable until ready. When ready, uncomment triggers in [.github/workflows/ci.yml](../.github/workflows/ci.yml). |

---

## 1. Strengths

### Clarity of purpose and boundaries

- **Mission and vision** are stated in the [Story](story/README.md): defensibility as a first-class, verifiable signal; "show your work" that can be verified, not just promised. The narrative is clear and avoids overclaiming.
- **Critical areas** (six documents) spell out what defensibility and "verified" do *not* guarantee (truth, source independence, verifier scope, evidence–claim validation, policy grounding, actor identity). This reduces over-trust and supports safe adoption.
- **Epistemology scope** and **verification guarantees** are documented; the technical report is citable and defines defensibility and the core schema precisely.

### Core deliverables

- **Standalone defensibility scorer** — Single entry point: (query, answer, evidence) in → defensibility JSON out. Implements a stable [eval contract](eval_contract.md) (v1.0) with JSON Schema; supports stdin, CLI flags, and evidence as strings, file paths, or URLs (with SSRF safeguards).
- **chronicle-verify** — Stdlib-only verifier for .chronicle (ZIP): manifest, schema, evidence hashes. Enables "verify it yourself" without the full stack. Web verifier exists for browser-based checks.
- **Chronicle package** — Event-sourced kernel (events, read model, projection), session API (ingest → claim → link → defensibility), and full command layer (claims, evidence, sources, tensions, reasoning brief, audit trail, as-of queries). Used by the scorer and by optional integrations.

### Eval and integration story

- **Eval contract** and **defensibility metrics schema** are stable and documented; harnesses can plug in without depending on implementation details.
- **RAG evals** doc is the single entry point for adding defensibility as a metric; [Integrating with Chronicle](integrating-with-chronicle.md) and [RAG in 5 minutes](rag-in-5-minutes.md) give a clear path for pipelines and one-command demos.
- **Optional integrations** (LangChain, LlamaIndex, Haystack) and **adapters** (RAG→scorer, fact-checker→Chronicle, provenance→Chronicle) are documented and scoped as optional; first-class vs optional is clear in [scripts/README](../scripts/README.md).

### Format and portability

- **.chronicle format** is specified (manifest, chronicle.db, evidence/); [chronicle file format](chronicle-file-format.md) and [consuming .chronicle](consuming-chronicle.md) allow producers and consumers to build without the Chronicle package.
- **Implementer checklist** gives a short produce/consume checklist with pointers.
- **Claim–evidence–metrics export** and **generic export** support fact-checking UIs and BI; external IDs and provenance recording support linking to external systems (we record, we don't verify).

### Documentation and onboarding

- **Story** (01–05) — Problem, why it exists, how we're solving it, challenges, how you can help. Audience is broad (not only engineers).
- **Lessons** (00–12) — Step-by-step codebase walkthrough with quizzes; Lesson 12 fully covers the .chronicle file format and data schema. Navigation (Previous | Index | Next) is consistent.
- **Docs index** ([docs/README](README.md)) and main [README](../README.md) give clear paths by persona (researchers, engineers, contributors). Glossary, troubleshooting, and errors doc exist.
- **Single to-do** — All pending work lives in [to_do](to_do.md); no scattered "future work" elsewhere. [State and plan](state-and-plan.md) describes current state without duplicating the to-do.

### Code and quality

- **Event-sourced design** — Append-only events; read model derived by projection; rebuild and as-of semantics documented. Schema lives in `chronicle/store/schema.py` and is applied on project init.
- **Ruff** for lint/format; **mypy** for type checking (strict for core, overrides for optional modules). **pytest** with coverage over core (scorer, session, verifier, identity, attestation, SSRF, audit trail, snapshot, event store, projection/commands).
- **Security** — SSRF safeguards on URL fetch in scorer; path traversal rejected in verifier. Scorer security and SSRF tests exist.
- **Error handling** — ChronicleUserError and related types; [errors](errors.md) doc describes when to use which and how CLI/API map to exit codes and status.

### Honesty and tone

- No unsupported claims, bragging, or competitor references in the scanned docs. Vision uses "verify (the package is well-formed)" to stay aligned with verification guarantees. Migration doc uses "focused RAG/evals story" instead of superlatives.

---

## 2. Weaknesses

### CI and coverage

- **CI triggers are disabled** — [.github/workflows/ci.yml](../.github/workflows/ci.yml) runs only on `workflow_dispatch`; push and pull_request are commented out. CONTRIBUTING states this explicitly. Consequence: no automatic lint/test on every push/PR until the maintainer re-enables triggers.
- **Coverage threshold mismatch** — `pyproject.toml` and [coverage-core](coverage-core.md) set `fail_under = 50%` for core code; the CI workflow still uses `--cov-fail-under=33`. So even when CI runs, it enforces a lower bar than the documented 50%. Coverage target is 75%; current config is 50%.
- **Coverage scope** — API, Neo4j, integrations, and optional LLM/tools are omitted from coverage so the bar applies to the defensibility path. That is intentional; the gap is the mismatch between CI and pyproject and the disabled triggers.

### Documentation sprawl and entry points

- **Many docs** — The repo has a large number of topic-based docs (eval contract, verifier, technical report, Neo4j, file format, consuming, generic export, claim–evidence export, external IDs, provenance, epistemology, AI to populate, Ollama, migration, state-and-plan, to-do, testing with Ollama, verification guarantees, implementer checklist, RAG in 5 minutes, human-in-the-loop, onboarding, getting started). The index and README help, but there is no single **user manual** (folder-per-chapter) yet; docs/README notes it is "planned under manual/."
- **Multiple "how to integrate" paths** — Getting started, RAG in 5 minutes, RAG evals doc, and Integrating with Chronicle all touch integration. They are consistent but could be summarized in one "Integration quick reference" (optional) so evaluators have a single place to look after the first run.

### Optional surface area

- **Optional extras** — API (`.[api]`), Neo4j (`.[neo4j]`), and integration packages (LangChain, etc.) are optional. New users who only run the scorer and verifier don't need them, but the distinction could be clearer in the very first paragraph of README (e.g. "Core install: `pip install -e .`; optional API or Neo4j: see docs."). Currently it's clear in Quick start and Docs.

### Release and packaging

- **No release automation** — CONTRIBUTING describes changelog + tag + push; to-do has "Future release" as a step. There is no automated release workflow or PyPI publish in CI; that may be intentional for now.
- **Version** — pyproject.toml has `version = "0.1.0"` and classifiers say "Pre-Alpha." Appropriate for current state.

---

## 3. Recommended new or improved features

### High priority

1. **Align CI with project policy**
   - Re-enable CI on push/PR when the maintainer is ready (uncomment triggers in [.github/workflows/ci.yml](../.github/workflows/ci.yml)).
   - Set `--cov-fail-under=50` in the workflow to match `pyproject.toml` and [coverage-core](coverage-core.md). Optionally add a note in CONTRIBUTING that CI and local coverage use the same value.

2. **Raise coverage toward 75%**
   - [to_do](to_do.md) and [coverage-core](coverage-core.md) already state that 75% for core is the target. Add a concrete to-do step (e.g. "Test coverage — phase 5: toward 75%; raise fail_under to 60% then 75%") and implement tests for remaining hot paths (e.g. export_import edge cases, CLI subcommands that use session, policy application in get_defensibility_score).

3. **User manual (optional but planned)**
   - docs/README says a user manual is planned under `manual/`. If you want a single vendor-style manual, add a minimal structure (e.g. `docs/manual/` with README as index and one chapter per major topic: install, scorer, verifier, .chronicle format, integration, limits). This can be incremental; the current topic-based docs can remain the source of truth.

### Medium priority

4. **One-line benchmark / reproducibility**
   - Add a single command or short section in README or [getting-started](getting-started.md) for "Generate the canonical sample set and run the defensibility benchmark" (e.g. point to `scripts/benchmark_data/run_defensibility_benchmark.py` and any env or sample-generation step). This helps papers and adopters reproduce results.

5. **Integration quick reference**
   - A single page (or a clearly titled section in getting-started or RAG evals) that lists: (1) Score one run (stdin/scorer), (2) Verify a .chronicle, (3) Add defensibility to your harness (contract + schema + scorer invocation), (4) Optional: session API, POST /score, adapters. Reduces the number of places an evaluator must look.

6. **Release checklist in CONTRIBUTING**
   - Expand "Changelog and releases" with a short checklist: update CHANGELOG, bump version if desired, tag, push tag, (optional) PyPI. This makes cutting a release repeatable without adding automation yet.

### Lower priority

7. **API and Neo4j in README**
   - In "What's in this repo," add one line: "Optional: HTTP API (`pip install -e '.[api]'`) and Neo4j sync (`.[neo4j]`) for project-based and graph workflows." So optional surface is visible at a glance.

8. **Coverage report in CI artifact**
   - Publish a coverage report (e.g. term-missing plus XML or HTML) as a CI artifact so reviewers can see which lines are uncovered without running locally.

9. **Stale link / doc checks**
   - Scripts like `check_doc_links.py` exist; consider running a link check in CI (or periodically) to catch broken internal links after renames or moves.

---

## 4. Summary table

| Area              | Strength | Weakness | Recommendation |
|-------------------|----------|----------|----------------|
| Purpose & limits  | Mission, vision, critical areas, epistemology scope | — | Keep; no change |
| Scorer & contract | Stable contract, schema, scorer, URL/path/SSRF       | — | No change |
| Verifier          | Stdlib-only, web verifier, guarantees doc           | — | No change |
| Format & consuming| File format, consuming doc, implementer checklist   | — | No change |
| Docs & onboarding | Story, lessons 00–12, quizzes, doc index            | Many topic docs; no manual yet | Optional manual; optional integration quick ref |
| Tests & CI        | Good core test set; coverage omit is clear          | CI disabled; CI uses 33% vs 50% | Re-enable CI; align cov threshold; raise toward 75% |
| To-do & state     | Single to-do; state-and-plan                        | — | Add phase 5 coverage step; release checklist |
| Tone & claims     | No overclaim or competitor refs                     | — | No change |

---

## 5. Next steps

- Add to [to_do](to_do.md): (1) Align CI `--cov-fail-under` with pyproject (50%); (2) Re-enable CI triggers when ready; (3) Test coverage phase 5 (toward 75%, raise fail_under stepwise); (4) Optional: integration quick reference; (5) Optional: user manual skeleton under `docs/manual/`.
- Optionally add a "Release checklist" subsection under CONTRIBUTING "Changelog and releases."
- Run the project (scorer, verifier, generate sample, verify) and one full lesson path to validate that the review matches actual experience; adjust recommendations if needed.
