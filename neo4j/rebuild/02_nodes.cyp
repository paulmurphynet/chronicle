// Neo4j nodes from relational read model. Spec 14.5.2, 14.7.1, 16.6, 16.9.1.
// Ghost-proof: MERGE by uid only; all nodes have uid, display_name, created_at.
// Run after 01_schema.cyp. CSVs from export (see chronicle.store.neo4j_export).

// Investigations
LOAD CSV WITH HEADERS FROM 'file:///investigations.csv' AS row
MERGE (i:Investigation {uid: row.investigation_uid})
ON CREATE SET
  i.display_name = coalesce(NULLIF(row.title, ''), row.investigation_uid),
  i.title = row.title,
  i.description = NULLIF(row.description, ''),
  i.is_archived = CASE WHEN row.is_archived IN ('1', 'true', 'True') THEN true ELSE false END,
  i.created_at = datetime(row.created_at),
  i.updated_at = datetime(row.updated_at)
ON MATCH SET
  i.title = coalesce(NULLIF(row.title, ''), i.title),
  i.description = coalesce(NULLIF(row.description, ''), i.description),
  i.is_archived = CASE WHEN row.is_archived IN ('1', 'true', 'True') THEN true ELSE false END,
  i.updated_at = coalesce(datetime(row.updated_at), i.updated_at);

// Sources
LOAD CSV WITH HEADERS FROM 'file:///sources.csv' AS row
MERGE (s:Source {uid: row.source_uid})
ON CREATE SET
  s.display_name = coalesce(NULLIF(row.display_name, ''), row.source_uid),
  s.source_type = row.source_type,
  s.alias = NULLIF(row.alias, ''),
  s.investigation_uid = row.investigation_uid,
  s.created_at = datetime(row.created_at)
ON MATCH SET
  s.display_name = coalesce(NULLIF(row.display_name, ''), s.display_name),
  s.source_type = coalesce(NULLIF(row.source_type, ''), s.source_type),
  s.alias = coalesce(NULLIF(row.alias, ''), s.alias);

// Claims
LOAD CSV WITH HEADERS FROM 'file:///claims.csv' AS row
MERGE (c:Claim {uid: row.claim_uid})
ON CREATE SET
  c.display_name = coalesce(NULLIF(row.claim_text, ''), row.claim_uid),
  c.claim_text = row.claim_text,
  c.claim_type = NULLIF(row.claim_type, ''),
  c.current_status = coalesce(NULLIF(row.current_status, ''), 'ACTIVE'),
  c.decomposition_status = coalesce(NULLIF(row.decomposition_status, ''), 'unanalyzed'),
  c.parent_claim_uid = NULLIF(row.parent_claim_uid, ''),
  c.investigation_uid = row.investigation_uid,
  c.created_at = datetime(row.created_at),
  c.updated_at = datetime(row.updated_at)
ON MATCH SET
  c.claim_text = coalesce(NULLIF(row.claim_text, ''), c.claim_text),
  c.claim_type = coalesce(NULLIF(row.claim_type, ''), c.claim_type),
  c.current_status = coalesce(NULLIF(row.current_status, ''), c.current_status),
  c.decomposition_status = coalesce(NULLIF(row.decomposition_status, ''), c.decomposition_status),
  c.parent_claim_uid = coalesce(NULLIF(row.parent_claim_uid, ''), c.parent_claim_uid),
  c.updated_at = coalesce(datetime(row.updated_at), c.updated_at);

// Evidence items (E2.3: provenance_type = human_created | ai_generated | unknown, optional)
LOAD CSV WITH HEADERS FROM 'file:///evidence_items.csv' AS row
MERGE (e:EvidenceItem {uid: row.evidence_uid})
ON CREATE SET
  e.display_name = coalesce(NULLIF(row.uri, ''), row.evidence_uid),
  e.content_hash = row.content_hash,
  e.uri = row.uri,
  e.media_type = row.media_type,
  e.created_at = datetime(row.created_at),
  e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE null END
ON MATCH SET
  e.uri = coalesce(NULLIF(row.uri, ''), e.uri),
  e.media_type = coalesce(NULLIF(row.media_type, ''), e.media_type),
  e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE e.provenance_type END;

// Evidence spans
LOAD CSV WITH HEADERS FROM 'file:///spans.csv' AS row
MERGE (s:EvidenceSpan {uid: row.span_uid})
ON CREATE SET
  s.display_name = coalesce(NULLIF(row.span_uid, ''), row.span_uid),
  s.anchor_type = row.anchor_type,
  s.anchor_json = row.anchor_json,
  s.created_at = datetime(row.created_at)
ON MATCH SET
  s.anchor_type = coalesce(NULLIF(row.anchor_type, ''), s.anchor_type),
  s.anchor_json = coalesce(NULLIF(row.anchor_json, ''), s.anchor_json);

// Actors (from events)
LOAD CSV WITH HEADERS FROM 'file:///actors.csv' AS row
MERGE (a:Actor {uid: row.actor_uid})
ON CREATE SET
  a.display_name = coalesce(NULLIF(row.display_name, ''), row.actor_uid),
  a.actor_type = row.actor_type
ON MATCH SET
  a.actor_type = coalesce(NULLIF(row.actor_type, ''), a.actor_type);

// Tensions
LOAD CSV WITH HEADERS FROM 'file:///tensions.csv' AS row
MERGE (t:Tension {uid: row.tension_uid})
ON CREATE SET
  t.display_name = coalesce(NULLIF(row.tension_uid, ''), row.tension_uid),
  t.kind = NULLIF(row.tension_kind, ''),
  t.status = coalesce(NULLIF(row.status, ''), 'OPEN'),
  t.created_at = datetime(row.created_at)
ON MATCH SET
  t.kind = coalesce(NULLIF(row.tension_kind, ''), t.kind),
  t.status = coalesce(NULLIF(row.status, ''), t.status);
