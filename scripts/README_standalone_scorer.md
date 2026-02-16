# Standalone defensibility scorer (M2)

Script and Docker image: (query, answer, evidence) in, defensibility JSON out. No API server or RAG stack. See [Eval contract](../docs/eval_contract.md).

## Run with Python (from repo root)

```bash
# Stdin
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py

# CLI flags
PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py \
  --query "What was revenue?" --answer "Revenue was $1.2M." \
  --evidence '["The company reported revenue of $1.2M in Q1 2024."]'
```

## Run with Docker

Build (from repo root):

```bash
docker build -f scripts/Dockerfile.standalone_scorer -t chronicle-scorer .
```

Stdin:

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | docker run -i chronicle-scorer
```

CLI flags:

```bash
docker run --rm chronicle-scorer --query "What was revenue?" --answer "Revenue was $1.2M." --evidence '["The company reported revenue of $1.2M in Q1 2024."]'
```

Exit code 0 on success, 1 on error. Output is one JSON object (metrics or error).
