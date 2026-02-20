PYTHON ?= ./.venv/bin/python
RUFF ?= ./.venv/bin/ruff
MYPY ?= ./.venv/bin/mypy
PYTEST ?= ./.venv/bin/pytest
POSTGRES_ENV_FILE ?= .env.postgres.local

.PHONY: help lint format-check typecheck test docs-check docs-currency neo4j-check adapter-check reference-workflows check postgres-env postgres-up postgres-down postgres-logs postgres-doctor postgres-smoke

help:
	@echo "Targets:"
	@echo "  lint         - Ruff lint for core Python modules"
	@echo "  format-check - Ruff format check"
	@echo "  typecheck    - Mypy type checks"
	@echo "  test         - Pytest suite"
	@echo "  docs-check   - Internal markdown link checks"
	@echo "  docs-currency - Check key docs/lessons/quizzes for current workflow references"
	@echo "  neo4j-check  - Neo4j export/sync/docs/rebuild contract parity checks"
	@echo "  adapter-check - Validate adapter examples and contract validation flow"
	@echo "  reference-workflows - Run reference workflow suite and write report under /tmp"
	@echo "  postgres-env - Create $(POSTGRES_ENV_FILE) from .env.postgres.example if missing"
	@echo "  postgres-up  - Start local Postgres via docker compose"
	@echo "  postgres-down - Stop local Postgres via docker compose"
	@echo "  postgres-logs - Tail local Postgres logs"
	@echo "  postgres-doctor - Check Postgres dependency + connectivity"
	@echo "  postgres-smoke - Run Postgres event-store smoke test"
	@echo "  check        - lint + typecheck + test + docs-check + docs-currency + neo4j-check + adapter-check + reference-workflows"

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

docs-currency:
	$(PYTHON) scripts/check_docs_currency.py

neo4j-check:
	$(PYTHON) scripts/check_neo4j_contract.py

adapter-check:
	$(PYTHON) scripts/adapters/check_examples.py

reference-workflows:
	$(PYTHON) scripts/run_reference_workflows.py --output-dir /tmp/chronicle_reference_workflows_check

check: lint typecheck test docs-check docs-currency neo4j-check adapter-check reference-workflows

postgres-env:
	@if [ -f "$(POSTGRES_ENV_FILE)" ]; then \
		echo "$(POSTGRES_ENV_FILE) already exists"; \
	else \
		cp .env.postgres.example "$(POSTGRES_ENV_FILE)"; \
		echo "Created $(POSTGRES_ENV_FILE) from .env.postgres.example"; \
	fi

postgres-up:
	@if [ ! -f "$(POSTGRES_ENV_FILE)" ]; then \
		cp .env.postgres.example "$(POSTGRES_ENV_FILE)"; \
		echo "Created $(POSTGRES_ENV_FILE) from .env.postgres.example"; \
	fi
	docker compose --env-file "$(POSTGRES_ENV_FILE)" -f docker-compose.postgres.yml up -d

postgres-down:
	docker compose --env-file "$(POSTGRES_ENV_FILE)" -f docker-compose.postgres.yml down

postgres-logs:
	docker compose --env-file "$(POSTGRES_ENV_FILE)" -f docker-compose.postgres.yml logs -f postgres

postgres-doctor:
	PYTHONPATH=. $(PYTHON) scripts/postgres_doctor.py --env-file "$(POSTGRES_ENV_FILE)"

postgres-smoke:
	PYTHONPATH=. $(PYTHON) scripts/postgres_smoke.py --env-file "$(POSTGRES_ENV_FILE)"
