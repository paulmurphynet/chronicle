# Lesson 09: Epistemic tools (decomposer, contradiction, type inference)

**Objectives:** You’ll know what the “epistemic tools” are: claim decomposition (atomic vs compound), tension/contradiction suggestion, and claim type/scope inference. You’ll see how they use optional LLM (Ollama) or heuristics and how they plug into the session.

**Key files:**

- [chronicle/tools/decomposer.py](../chronicle/tools/decomposer.py) — heuristic and LLM claim atomicity
- [chronicle/tools/contradiction.py](../chronicle/tools/contradiction.py) — heuristic and LLM tension suggestion
- [chronicle/tools/type_scope_inference.py](../chronicle/tools/type_scope_inference.py) — claim type and scope (LLM)
- [chronicle/tools/llm_client.py](../chronicle/tools/llm_client.py) — Ollama / OpenAI-compatible client
- [docs/using-ollama-locally.md](../docs/using-ollama-locally.md) — enable LLM and run tension suggestion

---

## What the epistemic tools do

They help **populate or refine** the epistemology of an investigation without you doing everything by hand:

1. **Decomposer** — Given a claim, is it one atomic fact or several? If several, suggest splits (e.g. “A and B” → claim A, claim B). Used when you want to decompose a compound claim into child claims so that evidence can be linked more precisely. **Heuristic**: split on conjunctions/sentence boundaries. **LLM**: ask the model to decide and suggest split texts.
2. **Contradiction (tension) suggestion** — Given a set of claims, which pairs are in tension? Produces **TensionSuggestion** (claim_a_uid, claim_b_uid, kind, confidence, rationale). User (or script) can then call **session.declare_tension(...)** to make them first-class tensions. **Heuristic**: overlap + opposite polarity (negation, success/failure). **LLM**: batch or single-pair “do these conflict?” with JSON output.
3. **Type/scope inference** — Suggest **claim type** (e.g. SEF, SAC, inference) or **scope** (temporal, geographic) for a claim. Optional enrichment for the read model.

All of these can run **without** an LLM (heuristic-only) or **with** a local LLM (e.g. Ollama). When the LLM is enabled (`CHRONICLE_LLM_ENABLED=1`), the session or scripts can call the LLM path; on failure or when disabled, they fall back to heuristics where available.

## Decomposer

Open **chronicle/tools/decomposer.py**.

- **analyze_claim_atomicity_heuristic(claim_text)** — Returns a **DecompositionResult** (is_atomic, suggested_splits, confidence, rationale). Splits on patterns like “ and ”, “ but ”, “;”, sentence boundaries.
- **analyze_claim_atomicity_llm(claim_text, client)** — Uses **LlmClient** to ask the model whether the claim is atomic and, if not, to suggest split texts. Returns the same shape. The **session** can call this when you run “decompose claim” (e.g. **analyze_claim_decomposition**); if the LLM is enabled it tries the LLM first, then falls back to heuristic.

## Contradiction (tension suggestion)

Open **chronicle/tools/contradiction.py**.

- **suggest_tensions_heuristic(claims)** — claims = list of (claim_uid, claim_text). Returns list of **TensionSuggestion**. Uses word overlap and opposite polarity (e.g. “failed” vs “succeeded”).
- **suggest_tensions_llm(claims, client, max_pairs=..., batch_size=...)** — Sends claim pairs to the LLM (batched or one-by-one), parses JSON (conflict, confidence, rationale, tension_kind), returns **TensionSuggestion** list. Used by **scripts/suggest_tensions_with_llm.py** so you can run tension suggestion over a project (heuristic or LLM) and optionally apply them.

## Type and scope inference

Open **chronicle/tools/type_scope_inference.py**.

- **suggest_claim_type_llm(claim_text, client)** — Returns a suggested claim type (e.g. SEF, SAC).
- **suggest_scope_llm(claim_text, client)** — Returns a suggested scope (temporal, geographic, etc.). Both are optional enrichment; the session or UI can call them when the user asks to “type” or “scope” a claim.

## LLM client

Open **chronicle/tools/llm_client.py**.

- **LlmClient** — Reads config from env (base URL, model, timeout, provider). **generate(prompt, system=...)** sends a chat request. **Provider**: `ollama` (local, no API key) or `openai_compatible` (hosted, Bearer key). Default is Ollama at http://127.0.0.1:11434 with model qwen2.5:7b. So “for free” local use is already supported; set **CHRONICLE_LLM_ENABLED=1** to turn the LLM on.

## Try it

1. Run **scripts/suggest_tensions_with_llm.py --path /path/to/project --method heuristic** (no LLM). You should see suggested tensions printed (or applied with --apply).
2. Set **CHRONICLE_LLM_ENABLED=1** and run with **--method llm** (and e.g. **--max-claims 100 --max-pairs 20**) to see the LLM path. Ensure Ollama is running and a model is pulled.

## Summary

- **Decomposer** — Atomic vs compound claim; heuristic or LLM; used when decomposing claims.
- **Contradiction** — Suggests which claim pairs are in tension; heuristic or LLM; **suggest_tensions_with_llm.py** runs it and can apply tensions.
- **Type/scope inference** — Optional LLM suggestions for claim type and scope.
- **LlmClient** — Ollama (default) or OpenAI-compatible; config via env; no API key for Ollama.

**Next:** [Lesson 10: Export, import, and Neo4j](10-export-import-neo4j.md)

**Quiz:** [quizzes/quiz-09-epistemic-tools.md](quizzes/quiz-09-epistemic-tools.md)
