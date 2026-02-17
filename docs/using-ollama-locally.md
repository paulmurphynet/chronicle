# Using Ollama locally for Chronicle (free AI)

Chronicle’s LLM-backed tools (tension suggestion, claim decomposition, type/scope inference) can use **Ollama** with no API key. Your local `qwen2.5:7b` (or any Ollama model) is enough.

---

## 1. Enable the LLM and point at Ollama

Defaults are already set for Ollama; you only need to turn the LLM **on**:

```bash
export CHRONICLE_LLM_ENABLED=1
```

Optional overrides (usually not needed):

| Env var | Default | Purpose |
|--------|---------|--------|
| `CHRONICLE_LLM_ENABLED` | `0` | Set to `1` or `true` to use LLM in session/scripts. |
| `CHRONICLE_LLM_PROVIDER` | `ollama` | `ollama` (local) or `openai_compatible` (hosted). |
| `CHRONICLE_LLM_BASE_URL` | `http://127.0.0.1:11434` | Ollama API URL. |
| `CHRONICLE_LLM_MODEL` | `qwen2.5:7b` | Model name (must exist in `ollama list`). |
| `CHRONICLE_LLM_TIMEOUT_SECONDS` | `60` | Request timeout. |

No API key is used for `ollama`. For embeddings (if you use them), `CHRONICLE_EMBEDDING_PROVIDER` defaults to `ollama` and uses the same base URL.

---

## 2. What uses the LLM

Once enabled, these use your local model:

- **Tension suggestion** — `suggest_tensions_llm()` in `chronicle/tools/contradiction.py` (e.g. via `scripts/suggest_tensions_with_llm.py`).
- **Claim decomposition** — When you run “decompose claim” in the session, it calls `analyze_claim_atomicity_llm()` if the LLM is enabled (otherwise heuristic).
- **Claim type/scope** — `suggest_claim_type_llm`, `suggest_scope_llm` in `chronicle/tools/type_scope_inference.py`.

All of these fall back to heuristic/non-LLM behavior on error or when the LLM is disabled.

---

## 3. Run tension suggestion with Ollama

From the repo root, with Ollama running and a model (e.g. `qwen2.5:7b`) available:

```bash
# Enable LLM (uses Ollama by default)
export CHRONICLE_LLM_ENABLED=1

# Heuristic-only (no Ollama): fast, many candidates
PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path test_data/lb_inquest/neo4j_project --method heuristic

# Use Ollama to suggest tensions (sample of claims, cap pairs)
PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path test_data/lb_inquest/neo4j_project --method llm --max-claims 500 --max-pairs 50

# Apply suggested tensions into the project (optional)
PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path test_data/lb_inquest/neo4j_project --method heuristic --apply
```

See `scripts/suggest_tensions_with_llm.py --help` for all options. For very large investigations (e.g. 25k claims), use `--max-claims` and `--max-pairs` so the LLM only sees a manageable subset; heuristic can still run over all claims.

---

## 4. Summary

- **Yes, you can use Ollama to do this work for free:** set `CHRONICLE_LLM_ENABLED=1`, leave provider/model at defaults (or set `CHRONICLE_LLM_MODEL=qwen2.5:7b`), and run the scripts or session commands that use the LLM.
- No API key required for Ollama; ensure `ollama serve` is running and the model is pulled (e.g. `ollama run qwen2.5:7b` once).
