// Optional: Neo4j Graph Data Science (GDS) examples for Chronicle graph.
// Requires Neo4j with the Graph Data Science library installed (e.g. Neo4j Desktop, AuraDS, or GDS plugin).
// See https://neo4j.com/docs/graph-data-science/current/
//
// Run after 01_schema, 02_nodes, 03_relationships. Create a graph projection first, then run algorithms.
// If procedure names or Cypher projection syntax differ in your GDS version, see the Neo4j GDS docs.

// =============================================================================
// Step 1: Create a named graph for Claim decomposition (Claim -[:DECOMPOSES_TO]-> Claim)
// Use this for centrality over the "claim hierarchy" (which claims have most children).
// =============================================================================
CALL gds.graph.project(
  'chronicle_claim_decomposition',
  'Claim',
  { DECOMPOSES_TO: { orientation: 'NATURAL' } }
)
YIELD graphName, nodeCount, relationshipCount;

// =============================================================================
// Step 2a: Degree centrality on decomposition (out-degree = number of child claims)
// Claims with highest score have the most direct children in the decomposition tree.
// =============================================================================
CALL gds.degree.stream('chronicle_claim_decomposition', { orientation: 'NATURAL' })
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).uid AS claim_uid, gds.util.asNode(nodeId).claim_text AS claim_text, score AS child_count
ORDER BY score DESC
LIMIT 20;

// =============================================================================
// Step 2b: PageRank on decomposition (importance in the tree)
// =============================================================================
CALL gds.pagerank.stream('chronicle_claim_decomposition')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).uid AS claim_uid, gds.util.asNode(nodeId).claim_text AS claim_text, score
ORDER BY score DESC
LIMIT 20;

// =============================================================================
// Step 3: Tension graph (claims connected by tensions) — Cypher projection
// Use for community detection: clusters of claims that contradict each other.
// =============================================================================
CALL gds.graph.project.cypher(
  'chronicle_tension_claims',
  'MATCH (c:Claim) RETURN id(c) AS id, c AS node',
  'MATCH (c1:Claim)<-[:BETWEEN]-(t:Tension)-[:BETWEEN]->(c2:Claim) WHERE c1 <> c2 RETURN id(c1) AS source, id(c2) AS target'
)
YIELD graphName, nodeCount, relationshipCount;

// =============================================================================
// Step 4: Louvain community detection on tension graph
// Groups claims into communities (e.g. clusters of claims in tension with each other).
// =============================================================================
CALL gds.louvain.stream('chronicle_tension_claims')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).uid AS claim_uid, gds.util.asNode(nodeId).claim_text AS claim_text, communityId
ORDER BY communityId, claim_uid;

// =============================================================================
// Cleanup (optional): drop projected graphs when done to free memory
// =============================================================================
// CALL gds.graph.drop('chronicle_claim_decomposition');
// CALL gds.graph.drop('chronicle_tension_claims');
