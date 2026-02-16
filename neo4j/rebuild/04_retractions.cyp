// Set retraction properties on SUPPORTS/CHALLENGES from link_retractions.csv.
// Spec: schemas.md 14.5.3, neo4j-pipeline.md 16.4. Run after 03_relationships.cyp.
// Safe to run when link_retractions.csv is empty (header only); no rows then no updates.

LOAD CSV WITH HEADERS FROM 'file:///link_retractions.csv' AS row
WHERE row.link_uid IS NOT NULL AND row.link_uid <> ''
MATCH (s:EvidenceSpan)-[r:SUPPORTS|CHALLENGES]->(c:Claim)
WHERE r.link_uid = row.link_uid
SET r.retracted_at = datetime(row.retracted_at),
    r.retracted_reason = CASE WHEN row.rationale IS NULL OR trim(row.rationale) = '' THEN null ELSE row.rationale END;
