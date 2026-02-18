# Onboarding and open-source readiness

This doc tracks **readiness for newcomers**. All **pending** work lives in [To-do](to_do.md). Use that for implementation steps and doc-update tasks.

---

## Checklist (current state)

These items are in place so the repo is usable for contributors and evaluators:

| Item | Status |
|------|--------|
| **README "New here?"** | Done — personas, two paths (understand vs run), guidebook, lessons, getting-started, glossary. |
| **CONTRIBUTING** | Done — dev setup, style (ruff, mypy), errors, changelog, coverage. |
| **Troubleshooting** | Done — [docs/troubleshooting.md](troubleshooting.md); common issues and fixes. |
| **Glossary** | Done — [docs/glossary.md](glossary.md); defensibility, claim, evidence, .chronicle, etc. |
| **Getting started** | Done — [docs/getting-started.md](getting-started.md); install, scorer, verifier, next steps. |
| **CHANGELOG** | Done — [CHANGELOG.md](../CHANGELOG.md); releases and tagged versions. |
| **Personas** | Done — README and docs: researchers/evaluators, engineers integrating, contributors. |
| **To-do as single list** | Done — [to_do.md](to_do.md) is the only place for pending implementation and doc-update tasks. |
| **.chronicle interchange** | Done — README positions .chronicle as "show your work"; encourage tooling that consumes it. |
| **Claim–evidence–metrics export** | Done — Helper `build_claim_evidence_metrics_export`; [claim-evidence-metrics-export.md](claim-evidence-metrics-export.md). |
| **Eval-harness integration** | Done — [integrating-with-chronicle.md](integrating-with-chronicle.md) (RAGAS/Trulens/LangSmith pattern, adapter template). |
| **Errors** | Done — [docs/errors.md](errors.md); ChronicleUserError, when to use which, CLI/API mapping. |
| **Example .chronicle** | Done — Try sample from `generate_sample_chronicle.py`; verifier doc has "Get a sample .chronicle." |

Guidebook, lessons, quizzes, and critical areas are updated **after** implementing new features so they stay in sync with the product.
