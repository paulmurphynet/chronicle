# How we’re solving it

We’re not trying to decide what’s true. We’re trying to make **how well a claim is supported** visible, scoreable, and verifiable—so you can judge and improve it.

---

## Evidence and claims

We treat **evidence** as first-class: immutable items (e.g. retrieved chunks or documents), often content-hashed so they can’t be changed without detection. **Claims** are the statements we care about—for example, the answer a RAG system produced. We don’t store “this is true”; we store that this claim was **proposed**, **linked** to evidence (support or challenge), and then we **compute** how defensible it is given those links and the rules you use.

---

## Defensibility score

We compute a **defensibility** result: strength of provenance, how many sources support the claim, whether there are open contradictions, and (optionally) temporal or knowability. That result is a **scorecard**—a stable shape that eval harnesses and tools can consume. “How defensible is this answer?” becomes a number and a structure, not a vague feeling.

---

## One run in, one score out

For RAG and evals, we keep the contract simple: **one (query, answer, evidence) in → one defensibility metrics object out.** No API server required. You can run our standalone scorer in a pipeline, or call the same logic from your own code. The fastest way to try it is **one command**: `chronicle quickstart-rag` (see [RAG in 5 minutes](../docs/rag-in-5-minutes.md)). For harness integration we document the path in [RAG evals: defensibility as a standard metric](../docs/rag-evals-defensibility-metric.md)—same contract and schema so your eval can plug in.

---

## .chronicle and “verify it yourself”

We also define a portable format: **.chronicle**. It’s a package (e.g. a ZIP) that contains the investigation’s manifest, schema, evidence, and claims. Anyone can **verify** it with our verifier—no need to run our full stack or trust us. So “show your work” becomes a **verifiable artifact**, not a promise. What “verified” means (and what the verifier does *not* check—e.g. truth of claims, source independence) is spelled out in [Verification guarantees](../docs/verification-guarantees.md). We also document [how to consume a .chronicle](../docs/consuming-chronicle.md) from another language or tool (open the ZIP, read the DB, resolve evidence), and an [implementer checklist](../docs/implementer-checklist.md) for producing or consuming the format.

---

## Event-sourced and auditable

Under the hood, we record **events**—every ingest, every claim, every link—and never erase them. So the story of how an answer was built is preserved. That supports auditing, debugging, and future extensions (e.g. “how defensible was this claim as of last Tuesday?”).

---

## Fitting into your ecosystem

We want Chronicle to work alongside fact-checking tools, provenance systems, and RAG pipelines:

- **Same shapes everywhere.** The defensibility scorecard and eval contract are stable and documented. Whether you use the standalone scorer, the session API, or the optional **HTTP API** ([docs/api.md](../docs/api.md)—install with `.[api]`, set a project path, run uvicorn), you get the same response shapes. That makes it easier for UIs and harnesses to swap one for another.
- **Adapters and terminology.** We provide example **adapters** (RAG→scorer, fact-checker output→Chronicle, provenance assertions→Chronicle) and a **terminology** table ([glossary](../docs/glossary.md#terminology-for-interop)) so you can map our terms (claim, support, challenge, tension) to yours (statement, evidence for/against, contradiction).
- **External IDs and provenance.** You can store **external IDs** (e.g. fact-check ID, C2PA claim ID) in evidence metadata and in claim **notes** or **tags** (one per claim) so “this Chronicle claim” lines up with “that external record.” We can **record** source and evidence–source links from provenance assertions (e.g. C2PA/CR); we don’t *verify* those assertions—we persist them so defensibility and reasoning trails can reference your provenance model. See [external IDs](../docs/external-ids.md) and [provenance recording](../docs/provenance-recording.md).
- **Claim–evidence–metrics and eval harnesses.** For fact-checking UIs and dashboards we provide a **claim–evidence–metrics** export (one claim + evidence refs + defensibility in a stable JSON shape); see [claim-evidence-metrics-export](../docs/claim-evidence-metrics-export.md). Eval frameworks (RAGAS, Trulens, LangSmith) can add defensibility as a custom metric; see [integrating with Chronicle](../docs/integrating-with-chronicle.md).
- **Human curation and attestation.** Every event records **who** did it (actor_id, actor_type). When a human (or tool) curates data—e.g. transcript ingestion, manual links—you can set your identity (CLI: **CHRONICLE_ACTOR_ID** / **--actor-id**; API: **X-Actor-Id** header) so the ledger attributes writes to you. Optionally, a **verification level** (e.g. from an IdP) can be stored so "attested with verified credential" is queryable. A [human-in-the-loop doc](../docs/human-in-the-loop-and-attestation.md) and a minimal **curation UI** (/static/curation.html with the API running) support this workflow.

If you’re building a fact-checking UI, a provenance pipeline, or a RAG eval harness, the [docs](../docs/) and [lessons](../lessons/README.md) walk through the contracts, schemas, and code paths so you can integrate without guessing.

---

**Next:** [04 — Where challenges remain](04-where-challenges-remain.md)
