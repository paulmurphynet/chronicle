# Supply-chain security automation

Chronicle includes a manual workflow for dependency scanning:

- Workflow: `.github/workflows/supply-chain.yml`
- Inputs: allowed thresholds for Python findings and npm high/critical findings
- Reports: uploaded as the `supply-chain-reports` artifact

## What runs

1. `pip-audit` for Python dependencies (`reports/pip-audit.json`)
2. `npm audit --json` for frontend dependencies (`reports/npm-audit.json`)
3. `scripts/supply_chain_gate.py` to enforce thresholds
   - Gate is fail-closed: malformed scan JSON, npm `error` payloads, or empty pip dependency audits fail the run.
4. Trivy filesystem + base image scans (`reports/trivy-fs.json`, `reports/trivy-postgres16.json`)
5. `scripts/container_security_gate.py` to enforce container high/critical thresholds

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

# Optional: container scan gate (requires Trivy installed)
trivy fs --format json --output reports/trivy-fs.json .
trivy image --format json --output reports/trivy-postgres16.json postgres:16
python3 scripts/container_security_gate.py \
  --report reports/trivy-fs.json \
  --report reports/trivy-postgres16.json \
  --max-high 0 \
  --max-critical 0
```

## Triage guidance

- If a report fails the gate, review whether the vulnerability is:
  - reachable in Chronicle runtime paths,
  - fixed by an available dependency update,
  - requiring a temporary exception with a documented expiry.
- Keep exceptions explicit in release notes or ADRs; do not silently relax thresholds.
