# Vertical sample generators

Each vertical has its own **sample generator** that produces a deterministic `.chronicle` file for "Try sample" and for tests.

## Layout

| Vertical   | Script                                      | Output (frontend/public)     |
|-----------|---------------------------------------------|------------------------------|
| Journalism| [journalism/generate_sample.py](journalism/generate_sample.py) | `sample.chronicle` (default) |
| Legal     | [legal/generate_sample.py](legal/generate_sample.py) | `sample_legal.chronicle` |
| History/Research | [history/generate_sample.py](history/generate_sample.py) | `sample_history.chronicle` |
| Compliance| [compliance/generate_sample.py](compliance/generate_sample.py) | `sample_compliance.chronicle` |
| Messy stress pack | [messy/generate_sample.py](messy/generate_sample.py) | `sample_messy.chronicle` |

## Run from repo root

```bash
PYTHONPATH=. python3 scripts/verticals/journalism/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/legal/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/history/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/compliance/generate_sample.py
PYTHONPATH=. python3 scripts/verticals/messy/generate_sample.py
```

## Quality gate

Run a deterministic quality/completeness check across all vertical samples:

```bash
PYTHONPATH=. python3 scripts/verticals/check_sample_quality.py
```

## Requirements

- **Deterministic:** Same script run twice should produce the same (or equivalent) output so CI can regenerate and verify.
- **Self-contained:** One investigation with evidence, claims, supports/challenges, sources + source links, and at least one tension. Copy the vertical policy profile to temp project so the manifest records `built_under_policy_id`.
- **Valid:** Output must pass `chronicle-verify path/to/sample.chronicle`.

## Examples as tests

CI can run each generator and then run the verifier on each output. See [Benchmark](../../docs/benchmark.md) and [Eval and benchmarking](../../docs/eval-and-benchmarking.md) for workflow guidance.
