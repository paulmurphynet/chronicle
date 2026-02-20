# Supply-chain security automation

Chronicle includes a manual workflow for dependency scanning:

- Workflow: `.github/workflows/supply-chain.yml`
- Inputs: allowed thresholds for Python findings and npm high/critical findings
- Reports: uploaded as the `supply-chain-reports` artifact

## What runs

1. `pip-audit` for Python dependencies (`reports/pip-audit.json`)
2. `npm audit --json` for frontend dependencies (`reports/npm-audit.json`)
3. `scripts/supply_chain_gate.py` to enforce thresholds

For release posture and operational hardening references, see:

- `docs/production-readiness-checklist.md`
- `docs/postgres-hardening.md`
- `docs/postgres-operations-runbook.md`

## Local run

From repo root:

```bash
python3 -m pip install --upgrade pip
pip install -e ".[dev]"
pip install pip-audit
cd frontend && npm install && cd ..
mkdir -p reports
pip-audit --format json --output reports/pip-audit.json || true
cd frontend && npm audit --json > ../reports/npm-audit.json || true && cd ..
python3 scripts/supply_chain_gate.py \
  --pip-report reports/pip-audit.json \
  --npm-report reports/npm-audit.json \
  --max-python-vulns 0 \
  --max-high 0 \
  --max-critical 0
```

## Triage guidance

- If a report fails the gate, review whether the vulnerability is:
  - reachable in Chronicle runtime paths,
  - fixed by an available dependency update,
  - requiring a temporary exception with a documented expiry.
- Keep exceptions explicit in release notes or ADRs; do not silently relax thresholds.
