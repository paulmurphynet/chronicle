# Realistic synthetic data

Generate synthetic `.chronicle` investigations that look like real use cases (revenue, outages, due diligence, RAG evals, compliance, support tickets) to test the Aura graph pipeline and see how the graph behaves with varied defensibility and tensions.

## Generate only

From repo root:

```bash
PYTHONPATH=. python scripts/synthetic_data/generate_realistic_synthetic.py
```

Writes 10 `.chronicle` files to `scripts/synthetic_data/output/`:

| File | Scenario | Profile |
|------|----------|---------|
| 01_acme_q3_revenue.chronicle | Acme Corp Q3 revenue | Strong (3 sources) |
| 02_nexus_outage.chronicle | Nexus API outage resolution | Challenged (support + challenge) |
| 03_meridian_merger.chronicle | Meridian merger target revenue | Resolved tension |
| 04_product_z_launch.chronicle | Product Z launch regions | Weak (single source) |
| 05_escalation_8841.chronicle | Customer refund timing | Challenged |
| 06_rag_founding_date.chronicle | RAG: company founding date | Strong |
| 07_compliance_control_72.chronicle | Compliance control 7.2 | Resolved tension |
| 08_competitor_pricing.chronicle | Competitor pricing | Strong (2 sources) |
| 09_witness_conflict.chronicle | Witness statements location | Open tension |
| 10_rag_availability.chronicle | RAG: product availability | Weak |

## Generate and ingest into Aura

To generate and then ingest all 10 files into your graph project and sync to Neo4j in one go:

```bash
PYTHONPATH=. python scripts/synthetic_data/generate_realistic_synthetic.py --ingest
```

Requires `.env` with `NEO4J_URI`, `NEO4J_PASSWORD` (and optionally `NEO4J_USER`, `CHRONICLE_GRAPH_PROJECT`). See [docs/aura-graph-pipeline.md](../../docs/aura-graph-pipeline.md).

## Ingest output manually

If you already generated and want to ingest later:

```bash
for f in scripts/synthetic_data/output/*.chronicle; do
  PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py "$f"
done
```
