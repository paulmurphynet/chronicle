// Neo4j 5.x schema: constraints and indexes for Chronicle graph projection.
// Spec: schemas.md 14.5, 14.5.4; neo4j-pipeline.md 16.5.
// Run first; idempotent.

CREATE CONSTRAINT investigation_uid_unique IF NOT EXISTS
FOR (i:Investigation) REQUIRE i.uid IS UNIQUE;

CREATE CONSTRAINT source_uid_unique IF NOT EXISTS
FOR (s:Source) REQUIRE s.uid IS UNIQUE;

CREATE CONSTRAINT claim_uid_unique IF NOT EXISTS
FOR (c:Claim) REQUIRE c.uid IS UNIQUE;

CREATE CONSTRAINT evidence_uid_unique IF NOT EXISTS
FOR (e:EvidenceItem) REQUIRE e.uid IS UNIQUE;

CREATE CONSTRAINT span_uid_unique IF NOT EXISTS
FOR (s:EvidenceSpan) REQUIRE s.uid IS UNIQUE;

CREATE CONSTRAINT actor_uid_unique IF NOT EXISTS
FOR (a:Actor) REQUIRE a.uid IS UNIQUE;

CREATE CONSTRAINT tension_uid_unique IF NOT EXISTS
FOR (t:Tension) REQUIRE t.uid IS UNIQUE;

CREATE INDEX claim_type_idx IF NOT EXISTS
FOR (c:Claim) ON (c.claim_type);

CREATE INDEX claim_status_idx IF NOT EXISTS
FOR (c:Claim) ON (c.current_status);

CREATE INDEX tension_status_idx IF NOT EXISTS
FOR (t:Tension) ON (t.status);

CREATE INDEX evidence_content_hash_idx IF NOT EXISTS
FOR (e:EvidenceItem) ON (e.content_hash);

CREATE INDEX supports_link_uid_idx IF NOT EXISTS
FOR ()-[r:SUPPORTS]-() ON (r.link_uid);

CREATE INDEX challenges_link_uid_idx IF NOT EXISTS
FOR ()-[r:CHALLENGES]-() ON (r.link_uid);

CREATE INDEX contains_claim_uid_idx IF NOT EXISTS
FOR ()-[r:CONTAINS_CLAIM]-() ON (r.claim_uid);

CREATE INDEX contains_evidence_uid_idx IF NOT EXISTS
FOR ()-[r:CONTAINS_EVIDENCE]-() ON (r.evidence_uid);
