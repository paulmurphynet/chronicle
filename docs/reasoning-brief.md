# Reasoning brief: primary shareable artifact per claim

The **reasoning brief** is the default shareable artifact for a single claim: it bundles the claim, its defensibility scorecard, supporting and challenging evidence, tensions with other claims, and the reasoning trail. Use it when you want to answer “why do you say that?” for one claim without handing over the whole .chronicle.

---

## What it is

- **One brief per claim.** It is assembled from the read model and event store: claim metadata, defensibility (provenance, corroboration, contradictions, etc.), support/challenge links with evidence references, tensions involving this claim, and the reasoning trail (events that affect the claim).
- **Stable shape.** The API and CLI return the same structure; you can also render it to HTML for human reading or to include in a submission package.

---

## When to use it (vs .chronicle)

| Use case | Prefer |
|----------|--------|
| Share “show your work” for **one claim** with a reviewer or editor | Reasoning brief (HTML or JSON) |
| Hand off a **full investigation** for verification or audit | .chronicle file (then verify with chronicle-verify) |
| Submission package for human review | ZIP with .chronicle + reasoning_briefs/ (HTML per claim) + manifest. See [Zero to submission](zero-to-submission.md). |
| Eval or pipeline: need **metrics only** | Defensibility endpoint or scorecard JSON; no need for full brief |

So: **reasoning brief = one-claim narrative + defensibility + evidence + trail**. **.chronicle = full investigation bundle** for verification and portability.

---

## Shape (summary)

The brief is a JSON object (or rendered HTML) with at least:

- **claim** — claim_uid, claim_text, claim_type, current_status, epistemic_stance (if set).
- **defensibility** — scorecard (provenance_quality, corroboration, contradiction_status, etc.; same as [defensibility metrics schema](defensibility-metrics-schema.md)).
- **support** / **challenge** — links with span_uid, evidence_uid, rationale, strength, integrity info.
- **tensions** — tensions involving this claim (claim_a, claim_b, kind, status).
- **reasoning_trail** — events that affect the claim (optional limit).
- **defensibility_as_of** — when a point-in-time defensibility snapshot was requested (optional).

Implementation details (sources, weakest link, correction trail, etc.) are in the code: [chronicle/store/commands/reasoning_brief.py](../chronicle/store/commands/reasoning_brief.py).

---

## How to get it

- **API:** `GET /claims/{claim_uid}/reasoning-brief` (optional query: `limit` for trail length). Returns JSON.
- **CLI:** `chronicle reasoning-brief <claim_uid>` (options for JSON vs HTML output). See `chronicle reasoning-brief --help`.
- **Submission package:** `POST /investigations/{id}/submission-package` produces a ZIP that includes `reasoning_briefs/{claim_uid}.html` for each claim (HTML rendered from the same brief).

---

## Related

- [Zero to submission](zero-to-submission.md) — path to a submission package (ZIP with .chronicle + reasoning_briefs/).
- [Defensibility metrics schema](defensibility-metrics-schema.md) — scorecard shape.
- [Verifier](verifier.md) — how to verify the .chronicle inside a submission package.
