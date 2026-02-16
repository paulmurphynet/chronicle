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

CREATE INDEX tension_status_idx IF NOT EXISTS
FOR (t:Tension) ON (t.status);
