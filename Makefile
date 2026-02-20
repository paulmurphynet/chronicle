PYTHON ?= ./.venv/bin/python
RUFF ?= ./.venv/bin/ruff
MYPY ?= ./.venv/bin/mypy
PYTEST ?= ./.venv/bin/pytest
POSTGRES_ENV_FILE ?= .env.postgres.local

.PHONY: help lint lint-all format-check format-check-all typecheck test docs-check docs-currency neo4j-check adapter-check integration-export-contract-check branch-protection-rollout-check deterministic-check reference-workflows check postgres-env postgres-up postgres-down postgres-logs postgres-doctor postgres-smoke postgres-parity postgres-onboarding-check

help:
	@echo "Targets:"
	@echo "  lint         - Ruff lint for release-gated core surfaces (chronicle + tools)"
	@echo "  lint-all     - Ruff lint for full repo Python surfaces (chronicle + tools + scripts + tests)"
	@echo "  format-check - Ruff format check for release-gated core surfaces (chronicle + tools)"
	@echo "  format-check-all - Ruff format check for full repo Python surfaces (chronicle + tools + scripts + tests)"
	@echo "  typecheck    - Mypy type checks"
	@echo "  test         - Pytest suite"
	@echo "  docs-check   - Internal markdown link checks"
	@echo "  docs-currency - Check key docs/lessons/quizzes for current workflow references"
	@echo "  neo4j-check  - Neo4j export/sync/docs/rebuild contract parity checks"
	@echo "  adapter-check - Validate adapter examples and contract validation flow"
	@echo "  integration-export-contract-check - Validate JSON/CSV/Markdown/signed-bundle integration export/import contracts"
	@echo "  branch-protection-rollout-check - Query GitHub API for branch protection + required CI green evidence (requires token)"
	@echo "  deterministic-check - Verify repeated scorer runs produce stable defensibility metrics"
	@echo "  reference-workflows - Run reference workflow suite and write report under /tmp"
	@echo "  postgres-env - Create $(POSTGRES_ENV_FILE) from .env.postgres.example if missing"
	@echo "  postgres-up  - Start local Postgres via docker compose"
	@echo "  postgres-down - Stop local Postgres via docker compose"
	@echo "  postgres-logs - Tail local Postgres logs"
	@echo "  postgres-doctor - Check Postgres dependency + connectivity"
	@echo "  postgres-smoke - Run Postgres event-store smoke test"
	@echo "  postgres-parity - Run SQLite vs Postgres defensibility parity check and write report"
	@echo "  postgres-onboarding-check - Run timed doctor+smoke onboarding check (<=10 minutes)"
	@echo "  check        - lint + typecheck + test + docs-check + docs-currency + neo4j-check + adapter-check + reference-workflows"

lint:
	$(RUFF) check chronicle tools

lint-all:
	$(RUFF) check chronicle tools scripts tests

format-check:
	$(RUFF) format --check chronicle tools

format-check-all:
	$(RUFF) format --check chronicle tools scripts tests

typecheck:
	$(MYPY) chronicle tools

test:
	CHRONICLE_EVENT_STORE=sqlite $(PYTEST) -q

docs-check:
	python3 scripts/check_doc_links.py docs
	python3 scripts/check_doc_links.py lessons
	python3 scripts/check_doc_links.py story
	python3 scripts/check_doc_links.py critical_areas

docs-currency:
	$(PYTHON) scripts/check_docs_currency.py

neo4j-check:
	$(PYTHON) scripts/check_neo4j_contract.py

adapter-check:
	$(PYTHON) scripts/adapters/check_examples.py

integration-export-contract-check:
	PYTHONPATH=. $(PYTHON) scripts/check_integration_export_contracts.py --project-path /tmp/chronicle_integration_contract_project --output-dir /tmp/chronicle_integration_contract_out

branch-protection-rollout-check:
	PYTHONPATH=. $(PYTHON) scripts/check_branch_protection_rollout.py --repo "$${GITHUB_REPOSITORY:?set GITHUB_REPOSITORY=owner/name}" --branch "$${CHRONICLE_PROTECTED_BRANCH:-main}" --output reports/branch_protection_rollout_report.json --stdout-json

deterministic-check:
	$(PYTHON) scripts/check_deterministic_defensibility.py --rounds 3 --output /tmp/chronicle_deterministic_defensibility_check.json

reference-workflows:
	$(PYTHON) scripts/run_reference_workflows.py --output-dir /tmp/chronicle_reference_workflows_check

check: lint format-check typecheck test docs-check docs-currency neo4j-check adapter-check integration-export-contract-check deterministic-check reference-workflows

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

postgres-parity:
	PYTHONPATH=. $(PYTHON) scripts/postgres_backend_parity.py --env-file "$(POSTGRES_ENV_FILE)"

postgres-onboarding-check:
	PYTHONPATH=. $(PYTHON) scripts/postgres_onboarding_timed_check.py --env-file "$(POSTGRES_ENV_FILE)"
