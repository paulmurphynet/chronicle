# How much AI to fully populate Chronicle’s epistemology?

Chronicle’s epistemology is **evidence → claims → support/challenge links → sources → tensions → defensibility**. “Fully populate” means filling every layer the schema supports from raw content (e.g. a transcript). This doc estimates **how much AI** is needed to do that **correctly** (not just structurally).

---

## What’s already there (structural or existing AI)

| Layer | Current state | AI today |
|-------|----------------|----------|
| **Evidence + spans** | Ingest creates one evidence item (and one span) per transcript line. | None |
| **Claims** | One claim per line (“Speaker: text”). | None |
| **Self-support** | Ingest links the span for that line to that claim (`link_support`). | None |
| **Tensions** | Heuristic + **LLM** in `chronicle/tools/contradiction.py`: `suggest_tensions_heuristic`, `suggest_tensions_llm`. User confirms → `TensionDeclared`. | Yes (optional LLM); heuristic is rule-based. |
| **Claim type/scope** | `chronicle/tools/type_scope_inference.py`: **LLM** suggests type (e.g. SEF, SAC) and scope. | Yes |
| **Decomposition** | `chronicle/tools/decomposer.py`: heuristic + **LLM** (`analyze_claim_atomicity_llm`) for compound → atomic. | Yes (optional LLM) |
| **Sources** | Schema: register source, link evidence to source, `independence_notes`. Not populated by transcript ingest. | None in ingest; independence is user judgment. |

So today: **structure** (evidence, claims, self-support) is automatic; **tensions, type, scope, decomposition** have optional AI; **sources** and **cross-evidence support/challenge** are the main gaps for “full” population.

---

## What “fully populate” adds (and what needs AI)

1. **Cross-evidence support and challenge**  
   For each claim, which **other** evidence spans (other lines, other docs) support or challenge it?  
   - **Correctly** means: real entailment/contradiction (or clear relevance), not noise.  
   - **AI needed:** High. You need to relate claim text to many evidence texts. Options:  
     - **NLI** (entailment/contradiction/neutral) over (claim, evidence) pairs: good for support/challenge, but you must **choose pairs** (e.g. embed claim + evidence, run NLI on top‑k candidates) to avoid O(claims × evidence) full matrix.  
     - **LLM** in batch: “Given this claim and this list of evidence snippets, which support and which challenge?” Same idea: reduce pairs (e.g. by embedding similarity or speaker/topic) then call LLM.  
   - **Volume:** For ~25k claims × ~25k evidence, a full matrix is infeasible. You need **retrieval** (embeddings, keyword, or structural filters like same-question/same-speaker) then **NLI or LLM on candidates**. So: embedding/indexing + many NLI/LLM calls (e.g. per claim or per batch of claims).  
   - **Summary:** **High AI** — retrieval + NLI or LLM; correctness depends on model quality and human review.

2. **Tensions at scale**  
   You already have heuristic + LLM suggestion; “full” means **run over (many) claim pairs** and curate.  
   - **AI needed:** Medium. Heuristic prunes pairs; LLM can refine. Bottleneck is **number of pairs**: O(C²). So you still need **filtering** (e.g. same topic, heuristic overlap, or embedding similarity) then batch LLM.  
   - **Summary:** **Medium AI** — same pattern as now, but scaled with filtering and batching; human confirm remains important.

3. **Sources and independence**  
   Register each speaker (or document) as a source; link each evidence item to a source; optionally add `independence_notes`.  
   - **Structural part:** Speaker → source, evidence → source can be done from transcript metadata. **No AI.**  
   - **Independence:** “Are these two sources independent?” is judgment. AI could **suggest** (e.g. “same witness” → not independent) but shouldn’t decide alone.  
   - **Summary:** **Low AI** (optional suggestions); main work is schema population and human notes.

4. **Claim type, scope, decomposition, link strength**  
   All have existing LLM hooks; “full” = run them over all claims/links.  
   - **AI needed:** Low–medium. One (or a few) calls per claim for type/scope/decomposition; per link for strength if you want it.  
   - **Summary:** **Low–medium AI**; correctness still benefits from human review.

5. **Warrant / “why”**  
   Chronicle does **not** model “why this span supports this claim” (no Toulmin warrant in the schema). So no AI “to fully populate” that layer — it’s out of scope (see [epistemology-scope.md](epistemology-scope.md)).

---

## Rough “AI intensity” for full population

| Task | Role of AI | Relative cost | Correctness |
|------|------------|---------------|-------------|
| Evidence, spans, claims, self-support | None (structural) | — | High (ingest logic) |
| **Cross-evidence support/challenge** | Retrieval + NLI or LLM | **High** (many pairs, filtered) | Model + human review |
| **Tensions** | Heuristic + LLM at scale | **Medium** (filtered pairs, batch LLM) | Model + human confirm |
| Sources (who said what) | Structural | — | High |
| Independence notes | Optional AI suggestion | Low | Human |
| Type, scope, decomposition, strength | Existing LLM | Low–medium | Model + human review |

So: **the main AI cost is cross-evidence support and challenge** (and, to a lesser extent, running tension suggestion at scale). The rest is either structural, or lower-volume LLM with existing tools.

---

## Practical takeaway

- **Minimal AI:** Keep current design: structure from ingest; optionally run **tension suggestion** (heuristic or LLM on a **filtered** set of pairs, e.g. by row id or known conflicts) and **sources** from transcript metadata. That gives you a **correctly** populated epistemology for “who said what” and “which stated claims conflict,” without claiming that every possible support/challenge is found.
- **Full epistemology:** Add **retrieval + NLI or LLM** for cross-evidence support/challenge (and scaled tension suggestion with filtering). That’s the only place you need “a lot” of AI; correctness will depend on model choice, prompt design, and human review rather than on Chronicle itself.

Chronicle’s defensibility stays **structural and policy-relative** either way; the AI only helps **populate** the graph, not certify truth (see [epistemology-scope.md](epistemology-scope.md) and [01-defensibility-is-not-truth.md](../critical_areas/01-defensibility-is-not-truth.md)).
