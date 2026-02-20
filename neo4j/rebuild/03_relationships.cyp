// Neo4j relationships from read model. Spec 14.5.3, 14.7.2, 16.7, 16.9.2.
// All relationships have source_event_id. Run after 02_nodes.cyp.

// Span IN EvidenceItem
LOAD CSV WITH HEADERS FROM 'file:///spans.csv' AS row
MATCH (s:EvidenceSpan {uid: row.span_uid})
MATCH (e:EvidenceItem {uid: row.evidence_uid})
MERGE (s)-[r:IN]->(e)
ON CREATE SET r.source_event_id = row.source_event_id;

// Support links (link_uid on relationship for retraction step 04)
LOAD CSV WITH HEADERS FROM 'file:///links.csv' AS row
WHERE row.link_type = 'SUPPORTS'
MATCH (s:EvidenceSpan {uid: row.span_uid})
MATCH (c:Claim {uid: row.claim_uid})
MERGE (s)-[r:SUPPORTS {link_uid: row.link_uid}]->(c)
ON CREATE SET
  r.source_event_id = row.source_event_id,
  r.rationale = NULLIF(row.rationale, '');

// Challenge links (link_uid on relationship for retraction step 04)
LOAD CSV WITH HEADERS FROM 'file:///links.csv' AS row
WHERE row.link_type = 'CHALLENGES'
MATCH (s:EvidenceSpan {uid: row.span_uid})
MATCH (c:Claim {uid: row.claim_uid})
MERGE (s)-[r:CHALLENGES {link_uid: row.link_uid}]->(c)
ON CREATE SET
  r.source_event_id = row.source_event_id,
  r.rationale = NULLIF(row.rationale, '');

// Assertions (Actor ASSERTS Claim)
LOAD CSV WITH HEADERS FROM 'file:///asserts.csv' AS row
MATCH (a:Actor {uid: row.actor_uid})
MATCH (c:Claim {uid: row.claim_uid})
MERGE (a)-[r:ASSERTS]->(c)
ON CREATE SET
  r.source_event_id = row.source_event_id,
  r.asserted_at = datetime(row.asserted_at),
  r.mode = row.mode,
  r.confidence = CASE WHEN row.confidence IS NULL OR row.confidence = '' THEN null ELSE toFloat(row.confidence) END;

// Tension BETWEEN claims (two edges)
LOAD CSV WITH HEADERS FROM 'file:///tensions.csv' AS row
MATCH (t:Tension {uid: row.tension_uid})
MATCH (c1:Claim {uid: row.claim_a_uid})
MATCH (c2:Claim {uid: row.claim_b_uid})
MERGE (t)-[r1:BETWEEN]->(c1)
ON CREATE SET r1.source_event_id = row.source_event_id
MERGE (t)-[r2:BETWEEN]->(c2)
ON CREATE SET r2.source_event_id = row.source_event_id;

// Evidence supersession
LOAD CSV WITH HEADERS FROM 'file:///supersession.csv' AS row
MATCH (eNew:EvidenceItem {uid: row.new_evidence_uid})
MATCH (ePrior:EvidenceItem {uid: row.prior_evidence_uid})
MERGE (eNew)-[r:SUPERSEDES]->(ePrior)
ON CREATE SET
  r.source_event_id = row.source_event_id,
  r.type = row.supersession_type,
  r.reason = NULLIF(row.reason, '');

// Claim decomposition (parent DECOMPOSES_TO child)
LOAD CSV WITH HEADERS FROM 'file:///decomposition_edges.csv' AS row
MATCH (parent:Claim {uid: row.parent_uid})
MATCH (child:Claim {uid: row.child_uid})
MERGE (parent)-[r:DECOMPOSES_TO]->(child)
ON CREATE SET r.source_event_id = row.source_event_id;

// Investigation CONTAINS Claim (from claim.investigation_uid)
LOAD CSV WITH HEADERS FROM 'file:///claims.csv' AS row
MATCH (i:Investigation {uid: row.investigation_uid})
MATCH (c:Claim {uid: row.claim_uid})
MERGE (i)-[r:CONTAINS]->(c)
ON CREATE SET r.source_event_id = '';

// EvidenceItem PROVIDED_BY Source
LOAD CSV WITH HEADERS FROM 'file:///evidence_source_links.csv' AS row
MATCH (e:EvidenceItem {uid: row.evidence_uid})
MATCH (s:Source {uid: row.source_uid})
MERGE (e)-[r:PROVIDED_BY]->(s)
ON CREATE SET
  r.source_event_id = row.source_event_id,
  r.relationship = NULLIF(row.relationship, '');
