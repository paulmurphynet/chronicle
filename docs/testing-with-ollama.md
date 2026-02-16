# Testing with Ollama (local LLM)

The project already supports **Ollama** as the default LLM backend. You can use it for real testing while developing, without an external API key.

## What uses the LLM

| Feature | Used by | When |
|---------|---------|------|
| **Chat/completions** | Decomposer, type/scope inference, contradiction detection, evidence-link suggestions, temporal suggestions | When `CHRONICLE_LLM_ENABLED` is set and the code path calls the LLM (e.g. session `analyze_claim_decomposition(use_llm=True)` or tools with `LlmClient`). |
| **Embeddings** | Optional semantic search / claim embedding | When `CHRONICLE_EMBEDDING_ENABLED` is set; uses Ollama embeddings (e.g. `nomic-embed-text`) by default. |

The **standalone defensibility scorer** does **not** call the LLM. It ingests evidence, proposes the claim, links evidence as support, and computes defensibility. So scorer tests and eval runs work without Ollama.

## Quick setup

1. **Install and run Ollama** (if not already):
   ```bash
   # Install from https://ollama.com; then:
   ollama serve   # usually already running as a service
   ```

2. **Pull a model** (default in code is `qwen2.5:7b`):
   ```bash
   ollama pull qwen2.5:7b
   ```
   Or use any other model (e.g. `llama3.2`, `mistral`) and set `CHRONICLE_LLM_MODEL` (see below).

3. **Enable the LLM** for Chronicle:
   ```bash
   export CHRONICLE_LLM_ENABLED=true
   ```
   Optional: set `CHRONICLE_LLM_MODEL=llama3.2` (or your model) if not using `qwen2.5:7b`.

4. **Run the scorer** (no LLM needed, but works either way):
   ```bash
   source .venv/bin/activate
   echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
     | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
   ```

5. **Run something that uses the LLM** (e.g. a script that calls session `analyze_claim_decomposition`, or the contradiction/type-inference tools). With `CHRONICLE_LLM_ENABLED=true` and Ollama running, those code paths will call your local model.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHRONICLE_LLM_ENABLED` | `false` | Set to `true` or `1` to enable LLM-backed tools. |
| `CHRONICLE_LLM_PROVIDER` | `ollama` | `ollama` (local) or `openai_compatible`. |
| `CHRONICLE_LLM_BASE_URL` | `http://127.0.0.1:11434` | Ollama (or OpenAI-compatible) base URL. |
| `CHRONICLE_LLM_MODEL` | `qwen2.5:7b` | Model name (Ollama tag or OpenAI model id). |
| `CHRONICLE_LLM_TIMEOUT_SECONDS` | `60` | Request timeout. |
| `CHRONICLE_LLM_API_KEY` | — | Only for `openai_compatible`; not used for Ollama. |

For **embeddings** (optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHRONICLE_EMBEDDING_ENABLED` | `false` | Set to `true` to enable embedding-based features. |
| `CHRONICLE_EMBEDDING_PROVIDER` | `ollama` | `ollama` or `openai_compatible`. |
| `CHRONICLE_EMBEDDING_BASE_URL` | `http://127.0.0.1:11434` | Same as LLM for local Ollama. |
| `CHRONICLE_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model. |

## Running tests with and without Ollama

- **Without Ollama** — Scorer and session tests that don’t call the LLM can run in CI or locally with no env set. LLM-backed features are skipped when `CHRONICLE_LLM_ENABLED` is not set (or the code uses heuristic-only paths).
- **With Ollama** — Set `CHRONICLE_LLM_ENABLED=true` and run your test or script; any code that uses `LlmClient` or `analyze_claim_decomposition(use_llm=True)` will hit your local Ollama. Useful for integration-style tests while developing.

If we add pytest later, we can use a marker (e.g. `@pytest.mark.ollama`) for tests that require Ollama and skip them when the env is unset or Ollama is unreachable, so CI stays fast and local runs can exercise the full stack.
