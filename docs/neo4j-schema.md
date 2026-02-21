# Neo4j graph schema (Chronicle sync)

When you export or sync a Chronicle project to Neo4j (see [Neo4j](neo4j.md)), the graph uses the following node labels, relationship types, and key properties. Graph RAG and other tools can query this schema without reverse-engineering the CSVs or sync logic.

## Node labels

| Label | Primary key | Key properties |
|-------|-------------|----------------|
| **Investigation** | `uid` (= investigation_uid) | title, description, is_archived, created_at, updated_at |
| **Source** | `uid` (= source_uid) | display_name, source_type, alias, investigation_uid |
| **Claim** | `uid` (= claim_uid) | claim_text, claim_type, current_status, decomposition_status, parent_claim_uid, investigation_uid, created_at, updated_at |
| **EvidenceItem** | `uid` (= evidence_uid) | uri, content_hash, media_type, provenance_type, created_at |
| **EvidenceSpan** | `uid` (= span_uid) | anchor_type, anchor_json, created_at |
| **Actor** | `uid` (= actor_uid) | display_name, actor_type |
| **Tension** | `uid` (= tension_uid) | kind, status, created_at |

All nodes have at least `uid` and typically `display_name` and `created_at` (where applicable).

## Relationship types

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| **CONTAINS** | Investigation → Claim | Investigation contains this claim. |
| **CONTAINS_CLAIM** | Investigation → Claim | Dedupe sync mode lineage edge; relationship stores original `claim_uid`. |
| **CONTAINS_EVIDENCE** | Investigation → EvidenceItem | Dedupe sync mode lineage edge; relationship stores original `evidence_uid`. |
| **IN** | EvidenceSpan → EvidenceItem | Span is a segment within this evidence item. |
| **SUPPORTS** | EvidenceSpan → Claim | This span supports the claim (`link_uid`, optional `rationale`, optional `retracted_at` on rel). |
| **CHALLENGES** | EvidenceSpan → Claim | This span challenges the claim (`link_uid`, optional `rationale`, optional `retracted_at` on rel). |
| **ASSERTS** | Actor → Claim | Actor asserted this claim (asserted_at, mode, confidence on rel). |
| **BETWEEN** | Tension → Claim | Tension is between two claims (one Tension has two BETWEEN edges). |
| **SUPERSEDES** | EvidenceItem → EvidenceItem | New evidence supersedes prior (type, reason on rel). |
| **DECOMPOSES_TO** | Claim → Claim | Parent claim decomposes to child claim. |
| **PROVIDED_BY** | EvidenceItem → Source | Evidence was provided by this source. |

Relationships usually carry `source_event_id` for traceability; `SUPPORTS`/`CHALLENGES` also have `link_uid` for retraction handling. In dedupe sync mode, lineage relationships (`CONTAINS_CLAIM`, `CONTAINS_EVIDENCE`) are keyed by original UIDs and do not currently carry `source_event_id`.

## Example Cypher queries

**Claims in tension with a given claim:**

```cypher
MATCH (c:Claim {uid: $claim_uid})
MATCH (t:Tension)-[:BETWEEN]->(c)
MATCH (t)-[:BETWEEN]->(other:Claim)
WHERE other <> c
RETURN DISTINCT other.uid AS claim_uid, other.claim_text, t.uid AS tension_uid, t.status AS tension_status;
```

**Evidence supporting a claim (active links only; excludes retracted):**

```cypher
MATCH (s:EvidenceSpan)-[r:SUPPORTS]->(c:Claim {uid: $claim_uid})
WHERE r.retracted_at IS NULL
MATCH (s)-[:IN]->(e:EvidenceItem)
RETURN s.uid AS span_uid, e.uid AS evidence_uid, e.uri AS evidence_uri;
```

More examples (lineage, contradiction network, GDS) are in [neo4j/rebuild/queries.cyp.example](../neo4j/rebuild/queries.cyp.example) and [neo4j/rebuild/gds_examples.cyp](../neo4j/rebuild/gds_examples.cyp). The rebuild scripts (01_schema.cyp through 04_retractions.cyp) define constraints and load from CSV; the sync path (chronicle neo4j-sync) MERGEs the same structure from the Chronicle read model.
