# Notebook examples

These notebooks are lightweight walkthroughs for interactive exploration.

Scope:

- They are examples/tutorials for researchers and evaluators.
- They are not a separate Chronicle UI product surface.

## Prerequisites

```bash
pip install chronicle-standard jupyter
```

For local source checkout:

```bash
pip install -e .
pip install jupyter
```

## Notebooks

- `notebooks/01-scorer-contract.ipynb`
  - Minimal scorer-contract run (`query`, `answer`, `evidence` -> scorecard JSON).
- `notebooks/02-session-workflow.ipynb`
  - End-to-end session workflow (create project, ingest evidence, propose claim, link support, inspect defensibility).

## Run

From repo root:

```bash
jupyter notebook
```

Open the notebook files above and run cells top-to-bottom.
