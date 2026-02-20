# Vertical sample generators

Each vertical has its own **sample generator** that produces a deterministic `.chronicle` file for "Try sample" and for tests.

## Layout

| Vertical   | Script                                      | Output (frontend/public)     |
|-----------|---------------------------------------------|------------------------------|
| Journalism| [journalism/generate_sample.py](journalism/generate_sample.py) | `sample.chronicle` (default) |
| Legal     | [legal/generate_sample.py](legal/generate_sample.py) | `sample_legal.chronicle` |
| History/Research | [history/generate_sample.py](history/generate_sample.py) | `sample_history.chronicle` |
| Compliance| *(to be added)*                           | `sample_compliance.chronicle` *(to be added)* |

## Run from repo root

```bash
PYTHONPATH=. python3 scripts/verticals/journalism/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/legal/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/history/generate_sample.py
```

## Requirements

- **Deterministic:** Same script run twice should produce the same (or equivalent) output so CI can regenerate and verify.
- **Self-contained:** One investigation, a few evidence items, claims, spans, links, at least one tension. Optionally copy the vertical's policy profile to the temp project before export so the manifest records `built_under_policy_id`.
- **Valid:** Output must pass `chronicle-verify path/to/sample.chronicle`.

## Examples as tests

CI can run each generator and then run the verifier on each output. See [Benchmark](../../docs/benchmark.md) and [Eval and benchmarking](../../docs/eval-and-benchmarking.md) for workflow guidance.
