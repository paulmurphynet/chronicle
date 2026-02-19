PYTHON ?= ./.venv/bin/python
RUFF ?= ./.venv/bin/ruff
MYPY ?= ./.venv/bin/mypy
PYTEST ?= ./.venv/bin/pytest

.PHONY: help lint format-check typecheck test docs-check neo4j-check reference-workflows check

help:
	@echo "Targets:"
	@echo "  lint         - Ruff lint for core Python modules"
	@echo "  format-check - Ruff format check"
	@echo "  typecheck    - Mypy type checks"
	@echo "  test         - Pytest suite"
	@echo "  docs-check   - Internal markdown link checks"
	@echo "  neo4j-check  - Neo4j export/sync/docs/rebuild contract parity checks"
	@echo "  reference-workflows - Run reference workflow suite and write report under /tmp"
	@echo "  check        - lint + typecheck + test + docs-check + neo4j-check + reference-workflows"

lint:
	$(RUFF) check chronicle tools

format-check:
	$(RUFF) format --check chronicle tools scripts tests

typecheck:
	$(MYPY) chronicle tools

test:
	$(PYTEST) -q

docs-check:
	python3 scripts/check_doc_links.py .

neo4j-check:
	$(PYTHON) scripts/check_neo4j_contract.py

reference-workflows:
	$(PYTHON) scripts/run_reference_workflows.py --output-dir /tmp/chronicle_reference_workflows_check

check: lint typecheck test docs-check neo4j-check reference-workflows
