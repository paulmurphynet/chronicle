# RAG in 5 minutes

Get from "Chronicle installed" to "my RAG run wrote evidence and a claim to Chronicle and I see defensibility" in under 5 minutes.

Already have (query, answer, evidence)? Use the [standalone defensibility scorer](eval_contract.md) for one-shot metrics JSON with no project. Building a pipeline? See [Integrating with Chronicle](integrating-with-chronicle.md) for the session API and minimum integration.

---

## One command

From the terminal (with Chronicle installed, e.g. `pip install -e .`):

```bash
chronicle quickstart-rag
```

This creates a temporary project, an investigation, ingests a short sample text as evidence, proposes one claim, links support, and prints defensibility and the claim UID.

**Example output:**

```
Project at: /tmp/chronicle_rag_xxxxx
Investigation: inv_...
Claim:        claim_...
Defensibility: medium
  Corroboration: {'support_count': 1, 'challenge_count': 0, ...}
  Contradiction:  none

View reasoning brief: chronicle reasoning-brief claim_... --path /tmp/chronicle_rag_xxxxx --format html > brief.html
```

Keep the project (e.g. for later inspection):

```bash
chronicle quickstart-rag --path /path/to/my_project
```

**Use your own text as evidence:**

```bash
chronicle quickstart-rag --path /path/to/my_project --text /path/to/document.txt
```

---

## What you get

- **Investigation** — One container for this RAG run.
- **Evidence** — The ingested text (or file) stored with a content hash.
- **Claim** — The proposed statement (e.g. the answer or extracted fact).
- **Support link** — The claim is linked to a span of the evidence so defensibility is computed.
- **Defensibility** — Provenance quality, corroboration, and contradiction status for the claim.

To view the full reasoning brief for the claim, run:

```bash
chronicle reasoning-brief <claim_uid> --path <project_path> --format html > brief.html
```

---

## Next steps

| Goal | Doc or command |
|------|----------------|
| Score one (query, answer, evidence) without a project | [Eval contract](eval_contract.md) — `scripts/standalone_defensibility_scorer.py` |
| Integrate your RAG pipeline (session API) | [Integrating with Chronicle](integrating-with-chronicle.md) |
| Run a fixed-query benchmark | [Benchmark](benchmark.md) — `scripts/benchmark_data/run_defensibility_benchmark.py --mode session` |
