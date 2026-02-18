# When to use Chronicle

Chronicle is built for **claims, evidence, defensibility, and verification**—not for general data lineage or ML pipeline provenance. This doc clarifies scope so integrators and contributors don’t stretch the system into problems it isn’t designed for.

---

## What Chronicle is for

- **Claims and evidence** — Propose claims, link evidence (support/challenge), model tensions between claims.
- **Defensibility** — Score how well a claim is supported (provenance, corroboration, contradictions); same contract for evals and human review.
- **Verification** — Export a `.chronicle` (ZIP) and verify it with `chronicle-verify` so others can check “show your work” without running your stack.
- **Human-in-the-loop** — Propose–confirm flows (e.g. tension suggestions), tier gating (Spark → Forge → Vault), attestation and actor identity. See [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md).

Use Chronicle when you need: **auditable claims**, **defensibility metrics**, **portable verification**, or **human-curated evidence and tensions**.

---

## What Chronicle is not

- **Data lineage** — Tracking where a dataset or column came from (e.g. dbt, OpenLineage, data catalogs). Those tools answer “where did this data come from?” Chronicle answers “how well is this claim supported by evidence?”
- **ML pipeline provenance** — Recording model versions, training runs, feature sets (e.g. MLflow, Kubeflow). Chronicle does not version models or track training pipelines; it records **claims and their evidence** so you can score defensibility and verify the record.
- **Generic workflow engine** — Chronicle is not a replacement for task queues or workflow orchestrators. It is a **ledger** for claims, evidence, and defensibility.

If your problem is “prove this claim with evidence and let others verify,” Chronicle fits. If it’s “trace this dataset through 10 systems” or “track every training run,” use or extend tools built for that.

---

## When to add Chronicle vs extend other tools

| Scenario | Prefer |
|----------|--------|
| RAG/QA: “Is this answer supported by retrieved docs?” | Add Chronicle (evidence = docs, claim = answer, link support/challenge). |
| Fact-checking or editorial: “Show your work for this assertion.” | Chronicle (reasoning brief, submission package, verifier). |
| Compliance/audit: “Prove who did what and how well claims are supported.” | Chronicle (events, attestation, defensibility, .chronicle export). |
| “Where did this table come from?” | Data lineage / catalog tools; optionally **feed** Chronicle with claims about the data. |
| “What model version produced this prediction?” | ML provenance tools; optionally **feed** Chronicle with claims and evidence about the prediction. |

You can **combine** Chronicle with lineage or ML tools: use them for lineage/provenance, and use Chronicle to record **claims** (e.g. “this metric is correct given this evidence”) and defensibility.

---

## Summary

- **Chronicle** = claims + evidence + defensibility + verification + human-in-the-loop.
- **Not Chronicle** = data lineage, ML pipeline provenance, generic workflows.
- **Add Chronicle** when you need defensibility, verification, or human-curated claim/evidence; **extend other tools** when you need lineage or run provenance, and optionally feed Chronicle with claims derived from them.

See [Epistemology scope](epistemology-scope.md) for what we do and don’t guarantee epistemically, and [Reference UI plan](reference-ui-plan.md) for the human-facing app that demonstrates the API.
