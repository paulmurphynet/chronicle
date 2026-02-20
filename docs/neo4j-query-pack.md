# Neo4j Query Pack and Indexing Guidance

This query pack provides production-focused Cypher patterns for Chronicle graph workflows.

Schema reference: [Neo4j schema](neo4j-schema.md)
Operations guidance: [Neo4j operations runbook](neo4j-operations-runbook.md)

## Assumptions

- Graph was loaded through `neo4j-export` rebuild scripts or `neo4j-sync`.
- `SUPPORTS` and `CHALLENGES` edges include `link_uid`.
- Dedupe mode adds `CONTAINS_CLAIM` / `CONTAINS_EVIDENCE` lineage edges.

## Query 1: Top unresolved tension clusters

```cypher
MATCH (t:Tension {status: 'OPEN'})-[:BETWEEN]->(c:Claim)
WITH t, collect(DISTINCT c.uid) AS claim_uids, count(DISTINCT c) AS claim_count
RETURN
  t.uid AS tension_uid,
  t.kind AS tension_kind,
  claim_count,
  claim_uids
ORDER BY claim_count DESC, tension_uid ASC
LIMIT 50;
```

Use this to rank unresolved contradiction hotspots for review queues.

## Query 2: Support/challenge balance by claim

```cypher
MATCH (c:Claim)
OPTIONAL MATCH (:EvidenceSpan)-[s:SUPPORTS]->(c)
OPTIONAL MATCH (:EvidenceSpan)-[ch:CHALLENGES]->(c)
WITH
  c,
  count(DISTINCT s) AS support_edges,
  count(DISTINCT ch) AS challenge_edges
RETURN
  c.uid AS claim_uid,
  c.claim_text AS claim_text,
  support_edges,
  challenge_edges,
  (support_edges - challenge_edges) AS support_minus_challenge
ORDER BY support_minus_challenge ASC, challenge_edges DESC
LIMIT 100;
```

Use this to detect claims that are weakly supported or heavily challenged.

## Query 3: Source concentration risk

```cypher
MATCH (c:Claim)<-[:SUPPORTS|CHALLENGES]-(:EvidenceSpan)-[:IN]->(e:EvidenceItem)-[:PROVIDED_BY]->(s:Source)
WITH c, collect(DISTINCT s.uid) AS sources
WITH c, size(sources) AS distinct_sources
RETURN
  c.uid AS claim_uid,
  c.claim_text AS claim_text,
  distinct_sources
ORDER BY distinct_sources ASC, claim_uid ASC
LIMIT 100;
```

Lower `distinct_sources` can indicate concentration or single-source dependence.

## Query 4: Investigation lineage traversal (dedupe mode)

```cypher
MATCH (i:Investigation {uid: $investigation_uid})-[cc:CONTAINS_CLAIM]->(c:Claim)
OPTIONAL MATCH (i)-[ce:CONTAINS_EVIDENCE]->(e:EvidenceItem)
RETURN
  i.uid AS investigation_uid,
  count(DISTINCT cc.claim_uid) AS lineage_claim_refs,
  count(DISTINCT ce.evidence_uid) AS lineage_evidence_refs,
  count(DISTINCT c) AS projected_claim_nodes,
  count(DISTINCT e) AS projected_evidence_nodes;
```

Use this when dedupe mode is enabled to verify investigation-level lineage cardinality.

## Query 5: Claim lineage subgraph (dedupe mode)

```cypher
MATCH (i:Investigation {uid: $investigation_uid})-[cc:CONTAINS_CLAIM]->(c:Claim)
OPTIONAL MATCH (s:EvidenceSpan)-[:SUPPORTS|CHALLENGES]->(c)
OPTIONAL MATCH (s)-[:IN]->(e:EvidenceItem)
RETURN
  cc.claim_uid AS lineage_claim_uid,
  c.uid AS claim_node_uid,
  c.claim_text AS claim_text,
  collect(DISTINCT e.uid) AS related_evidence_node_uids
LIMIT 200;
```

Use this to explain dedupe-mode identity: lineage references (`claim_uid`) vs shared claim nodes (`c.uid` hash).

## Query 6: Retracted edge audit

```cypher
MATCH (:EvidenceSpan)-[r:SUPPORTS|CHALLENGES]->(:Claim)
WHERE r.retracted_at IS NOT NULL
RETURN
  r.link_uid AS link_uid,
  type(r) AS link_type,
  r.retracted_at AS retracted_at,
  r.retracted_reason AS retracted_reason
ORDER BY r.retracted_at DESC
LIMIT 200;
```

Use this for withdrawal/retraction review workflows.

## Index and constraint guidance

Baseline constraints/indexes are created by Chronicle sync/rebuild schema:

- Unique node `uid` constraints: `Investigation`, `Source`, `Claim`, `EvidenceItem`, `EvidenceSpan`, `Actor`, `Tension`
- Property indexes: `Claim.claim_type`, `Claim.current_status`, `Tension.status`, `EvidenceItem.content_hash`
- Relationship property indexes: `SUPPORTS.link_uid`, `CHALLENGES.link_uid`, `CONTAINS_CLAIM.claim_uid`, `CONTAINS_EVIDENCE.evidence_uid`

Recommended additions for large workloads:

1. Add `Source.source_type` index when source-type filtering is common.
2. Add `Investigation.updated_at` index when pagination/sorting by freshness is common.
3. Keep query predicates anchored on indexed labels/properties before deep traversals.

## Query-pack validation checklist

For release validation:

1. Run all query-pack statements against a freshly synced graph.
2. Capture timing for at least:
   - Query 1 (tension triage)
   - Query 2 (support/challenge balance)
   - Query 4 (lineage validation in dedupe mode)
3. Record latencies and cardinalities in release evidence artifacts.
