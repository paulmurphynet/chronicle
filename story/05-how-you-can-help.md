# How you can help

The first three chapters described the problem, why it exists, and how we’re solving it. The fourth spelled out where challenges remain and what we don’t promise. This one is about **you**: how you can make defensibility a first-class, verifiable part of how the world evaluates and trusts answers. Chronicle is better when more people contribute—code, feedback, docs, or simply by spreading the story. Here are concrete ways to help.

---

## If you write code

- **Try the one-command RAG path.** Run `chronicle quickstart-rag` (see [RAG in 5 minutes](../docs/rag-in-5-minutes.md)). Then run the **scorer** and **verifier** and report what works and what doesn’t. File issues or suggest improvements.
- **Add defensibility to your evals.** Use the [eval contract](../docs/eval_contract.md) and the standalone scorer (or the session API) and share your experience—what was easy, what was missing. The [RAG evals](../docs/rag-evals-defensibility-metric.md) doc is the single entry point for “Chronicle defensibility as a standard metric” in your harness.
- **Try the optional HTTP API or adapters.** Install with `pip install -e ".[api]"`. Use **POST /score** for scorer-as-a-service (no project path; same eval contract). For full project-based API (investigations, claims, links, export), set `CHRONICLE_PROJECT_PATH` and run uvicorn. Or use the [adapters](../scripts/adapters/) (RAG→scorer, fact-checker→Chronicle, provenance→Chronicle) as templates. See [docs/api.md](../docs/api.md) and [docs/provenance-recording.md](../docs/provenance-recording.md).
- **Try Neo4j sync with deduplication.** If you use the graph pipeline ([aura-graph-pipeline](../docs/aura-graph-pipeline.md)), run `chronicle neo4j-sync --path <project> --dedupe-evidence-by-content-hash` (or set `NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1`) for full evidence and claim deduplication and report how it behaves at your scale.
- **Run tests and CI.** We have tests for the scorer, session flow, and verifier; CI runs ruff and pytest on push/PR. Run `pytest tests/ -v` locally (after `pip install -e ".[dev]"`) and keep the suite green when you change code.
- **Contribute to the repo.** We have a [to-do list](../docs/to_do.md). Pick an item, open a PR, or discuss in an issue.
- **Use the lessons.** If you’re new to the codebase, go through the [lessons](../lessons/README.md) (00–12), including [Lesson 11](../lessons/11-interoperability-api-and-tests.md) on interop, API, and tests, and [Lesson 12](../lessons/12-chronicle-file-format-and-schema.md) on the full .chronicle file format and data schema. If something is wrong or unclear, suggest a change.
- **Human-curated data and attestation.** If you run ingestion or curation (e.g. transcripts, manual links), set actor identity (CLI: `CHRONICLE_ACTOR_ID` / `--actor-id`; API: `X-Actor-Id` header) so the ledger attributes who did what. See [Human-in-the-loop and attestation](../docs/human-in-the-loop-and-attestation.md) for the full workflow.

---

## If you write or teach

- **Reference the technical report and the contract.** If you teach or publish in the space of RAG, evals, or evidence-based systems, citing our [technical report](../docs/technical-report.md) and [eval contract](../docs/eval_contract.md) helps others find us and understand defensibility.
- **Improve the story or docs.** The [story](README.md) is for everyone. If a sentence is confusing or a chapter is missing, suggest an edit or open a PR. Same for the main [docs](../docs/) (eval contract, verifier, verification guarantees, implementer checklist, RAG in 5 minutes, API, human-in-the-loop and attestation, consuming .chronicle, external IDs, provenance, RAG evals, etc.).

---

## If you evaluate or build RAG systems

- **Try Chronicle in your pipeline.** Add the defensibility scorer as a metric and see how it behaves on your data. Use the [RAG evals doc](../docs/rag-evals-defensibility-metric.md) for the contract, schema, and how to run the scorer. Your feedback—what’s useful, what’s noisy, what’s missing—shapes what we do next.
- **Read the [critical areas](../critical_areas/README.md)** so you know what the score does and doesn’t guarantee (e.g. defensibility is not truth; source independence is not verified). That keeps evals and reports honest.
- **Share benchmarks or case studies.** If you run defensibility at scale or in a particular domain, sharing (anonymized) lessons or numbers helps the community and us.

---

## If you just care about the problem

- **Share the story.** Point people to the [story](README.md) or the repo when the topic of “show your work,” evidence-based answers, or RAG evals comes up.
- **Tell us what you need.** Open an issue or start a discussion: “We need X to adopt this” or “We tried Y and it didn’t work.” That feedback is how we prioritize.

---

We’re a small effort with a clear goal: make defensibility a first-class, verifiable part of how the world evaluates and trusts answers. Every bit of help—code, docs, testing, or word of mouth—gets us closer. Thank you for reading, and for caring about “show your work.”

**← Previous:** [04 — Where challenges remain](04-where-challenges-remain.md) | **Index:** [Story](README.md) | **Next →:** [06 — Epistemology: what we implement and what we don’t](06-epistemology-scope-tables.md)
