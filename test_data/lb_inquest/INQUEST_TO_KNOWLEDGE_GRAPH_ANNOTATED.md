# From `inquest.csv` to Case Analysis in a Knowledge Graph

Annotated, realistic guide for processing the Lizzie Borden inquest transcript with Chronicle and Neo4j.

---

## 1. What this guide is (and is not)

This guide explains what happens when you process `test_data/lb_inquest/inquest.csv` all the way into a Chronicle-backed Neo4j graph, and which parts are:

1. Automated by Chronicle.
2. AI-assisted (optional).
3. Human judgment and decision-making.

**Important boundary:** "Fully accurate analysis" is not a purely technical state. Chronicle can guarantee structure and reproducibility; it cannot guarantee historical truth.

**Annotation:** This boundary is explicit in Chronicle docs (see `docs/case-study-lizzie-borden.md` and `docs/verification-guarantees.md`).

---

## 2. The pipeline at a glance

1. Ingest transcript CSV into Chronicle structure (evidence, spans, claims, support links).
2. Export `.chronicle`.
3. Verify `.chronicle` integrity.
4. Import into a graph project.
5. Sync graph project to Neo4j.
6. Enrich with tensions/challenges/sources and re-sync.
7. Perform analysis queries in Neo4j.

**Annotation:** This corresponds directly to `scripts/ingest_transcript_csv.py` and `scripts/ingest_chronicle_to_aura.py`.

---

## 3. What Chronicle does automatically

When you run `scripts/ingest_transcript_csv.py`:

1. Creates a Chronicle project.
2. Creates an investigation.
3. For each row in CSV:
   - ingests evidence text,
   - anchors a full-text span,
   - proposes a claim (usually `speaker: testimony`),
   - links that span as support for the claim.
4. Exports the investigation as `.chronicle`.

**Annotation:** This is deterministic transformation logic, not model inference.

### What this guarantees

1. Every processed row has traceable ledger events.
2. Evidence/claim links are explicit and queryable.
3. Export can be verified with `chronicle verify-chronicle`.
4. Graph projection can be repeated from the same artifacts.

### What this does not guarantee

1. That each row-level claim is semantically ideal.
2. That support/challenge balance is complete.
3. That contradictions are fully identified.
4. That resulting interpretation is historically correct.

---

## 4. Where AI can help (optional, useful, not final authority)

AI is useful for semantic enrichment after baseline ingest:

1. Suggesting contradictions/tensions across claims.
2. Splitting compound claims into atomic claims.
3. Suggesting challenge links (not just support links).
4. Grouping similar claims by topic/semantic overlap.

**Annotation:** In this repo, contradiction suggestion is available via `scripts/suggest_tensions_with_llm.py` (`--method llm` or `--method heuristic`).

### AI's role in this workflow

1. **Proposal generation**, not adjudication.
2. **Recall booster** for potential conflicts.
3. **Triage assistant** for human review queues.

### Why AI cannot be the final decider

1. Historical language is ambiguous and context-heavy.
2. Model outputs can be fluent but unsupported.
3. Legal/historical judgments require policy and domain judgment.

---

## 5. Where humans are required

Human decisions are essential at these points:

1. **Scope policy:** what corpus is in-scope and what is out-of-scope.
2. **Claim quality:** whether generated claim text is atomic and faithful.
3. **Conflict adjudication:** whether an AI-suggested tension is real, duplicate, weak, or resolved.
4. **Challenge linking:** adding explicit counter-evidence links where needed.
5. **Interpretation layer:** deriving case-level conclusions from contested records.
6. **Publication controls:** deciding what can be reported as supported vs unresolved.

**Annotation:** Chronicle is built to record these decisions (actor-attributed events), not to erase them.

---

## 6. Realistic command workflow (end-to-end)

## 6.1 Baseline ingest

```bash
CHRONICLE_ACTOR_ID=curator \
./.venv/bin/python scripts/ingest_transcript_csv.py \
  test_data/lb_inquest/inquest.csv \
  --text-col testimony \
  --speaker-col speaker \
  --title "Lizzie Borden inquest" \
  --out test_data/lb_inquest/out/01_raw_full.chronicle
```

**Annotation:** This creates broad structural coverage quickly for all 3,856 rows.

## 6.2 Import into working project for enrichment

```bash
./.venv/bin/chronicle init test_data/lb_inquest/work_project
./.venv/bin/chronicle import \
  test_data/lb_inquest/out/01_raw_full.chronicle \
  --path test_data/lb_inquest/work_project
```

## 6.3 Add known tensions and suggested tensions

```bash
./.venv/bin/python scripts/add_lizzie_tensions.py \
  --project test_data/lb_inquest/work_project

./.venv/bin/python scripts/suggest_tensions_with_llm.py \
  --path test_data/lb_inquest/work_project \
  --method heuristic \
  --max-claims 5000 \
  --apply
```

**Annotation:** `heuristic` is deterministic and easier to audit; `llm` can improve recall but needs tighter review.

## 6.4 Export enriched Chronicle artifact

```bash
INV_UID=$(./.venv/bin/python - <<'PY'
from chronicle.store.session import ChronicleSession
with ChronicleSession("test_data/lb_inquest/work_project") as s:
    print(s.read_model.list_investigations()[0].investigation_uid)
PY
)

./.venv/bin/chronicle export \
  --path test_data/lb_inquest/work_project \
  --investigation "$INV_UID" \
  --output test_data/lb_inquest/out/02_enriched.chronicle
```

## 6.5 Verify and sync all resulting artifacts to Neo4j

```bash
./.venv/bin/chronicle init test_data/lb_inquest/graph_project

for f in test_data/lb_inquest/out/*.chronicle; do
  ./.venv/bin/chronicle verify-chronicle "$f" || exit 1
  ./.venv/bin/chronicle import "$f" --path test_data/lb_inquest/graph_project || exit 1
done

./.venv/bin/chronicle neo4j-sync \
  --path test_data/lb_inquest/graph_project \
  --dedupe-evidence-by-content-hash \
  --progress \
  --report reports/lizzie_sync.json
```

**Annotation:** Using multiple `.chronicle` snapshots allows versioned analysis states rather than one opaque mutable state.

---

## 7. What "complete graph coverage" actually means

To approach full Chronicle schema coverage in Neo4j (see `docs/neo4j-schema.md`), you need more than row->support links.

### Usually present after baseline ingest

1. `Investigation`
2. `Claim`
3. `EvidenceItem`
4. `EvidenceSpan`
5. `SUPPORTS`
6. basic containment/inclusion edges

### Requires enrichment passes

1. `CHALLENGES` links (counter-evidence).
2. `Tension` nodes and `BETWEEN` edges.
3. `Source` nodes and `PROVIDED_BY` edges.
4. `DECOMPOSES_TO` (if using claim decomposition).
5. `SUPERSEDES` (if evidence revisions are tracked).

**Annotation:** Baseline ingest is broad and fast; enrichment creates analytical depth.

---

## 8. Accuracy model: structural accuracy vs interpretive accuracy

## 8.1 Structural accuracy (Chronicle can enforce strongly)

1. Hash-verifiable evidence packaging.
2. Deterministic transforms and replayable event history.
3. Stable claim/evidence/tension graph edges.
4. Repeatable export/import/sync process.

## 8.2 Interpretive accuracy (requires humans + policy)

1. Meaning of witness statements.
2. Reliability weighting of sources.
3. Resolution of ambiguous testimony.
4. Final conclusions about contested events.

**Practical rule:** Treat Chronicle defensibility as a quality signal over evidence structure, not a machine verdict on truth.

---

## 9. Decision log template for review teams

For each disputed cluster of claims:

1. `cluster_id`
2. claims reviewed
3. evidence spans reviewed
4. AI suggestions accepted/rejected and reason
5. tensions declared/updated
6. unresolved questions
7. reviewer + timestamp

**Annotation:** Keep this in repo docs or review packets to preserve analytical provenance outside ad-hoc notes.

---

## 10. Common failure modes and mitigations

1. **Failure:** row-level claims are too literal or too broad.
   - **Mitigation:** add decomposition pass and curated claim normalization.

2. **Failure:** only support links exist, no challenges.
   - **Mitigation:** targeted contradiction review and challenge-link authoring.

3. **Failure:** AI overflags contradictions.
   - **Mitigation:** human adjudication queue and confidence thresholds.

4. **Failure:** graph appears "complete" but is semantically shallow.
   - **Mitigation:** define minimum enrichment criteria before analysis publication.

5. **Failure:** conclusions presented as certain despite unresolved tensions.
   - **Mitigation:** require explicit unresolved-tension section in final reporting.

---

## 11. Recommended publication standard for this case study

Before publishing analysis outputs, require:

1. Verified `.chronicle` artifact(s).
2. Documented enrichment process (heuristic/LLM/manual splits).
3. Reviewer decision log for major tension clusters.
4. Clear separation of:
   - supported findings,
   - contested findings,
   - unresolved findings.

This is the difference between a technically impressive graph and a defensible analytical product.

---

## 12. Bottom line

Chronicle can automate the heavy lifting of turning the full transcript into a verifiable reasoning graph. AI can accelerate enrichment. Human reviewers remain responsible for epistemic decisions and final interpretation.

If you want "fully accurate analysis," treat accuracy as a governance process over a structured ledger, not as a one-shot output of ingestion or model inference.

