# Quiz 10: Export, import, and Neo4j

**Lesson:** [10-export-import-neo4j.md](../10-export-import-neo4j.md)

Answer these after reading the lesson and the export_import/neo4j_sync code. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What are the **three** main contents of a **.chronicle** ZIP file?

2. When you **import** a .chronicle into a project, what happens to the events in the .chronicle? (Appended to the project’s store? Replaced?)

3. What does **sync_project_to_neo4j** do in one sentence? (What is pushed where?)

4. Why is the **evidence/** folder inside a .chronicle just “raw files” (e.g. one text file per evidence item) and not a structured format? Where is the **structure** (claims, links, tensions) stored?

5. Which script implements the full pipeline: verify a .chronicle → import into a graph project → sync to Neo4j?

---

## Answer key

1. **manifest.json** (format_version, investigation_uid, title, etc.), **chronicle.db** (SQLite with events and read model for that investigation), **evidence/** (one file per evidence item, paths from evidence_item.uri).

2. The events from the .chronicle are **appended** to the project’s event store (with idempotency where possible). So import **merges** the investigation into the project; the project’s projection runs and the read model then includes the imported investigation.

3. **sync_project_to_neo4j** reads the **project’s read model** (all investigations, claims, evidence, links, tensions) and **pushes** them to Neo4j as nodes and relationships (Investigation, Claim, EvidenceItem, SUPPORTS, CHALLENGES, Tension, etc.), typically using MERGE so re-sync is idempotent.

4. The **evidence** folder holds only the **raw content** (blobs) of each evidence item. The **structure** (which claim, which links, which tensions) is in the **chronicle.db** SQLite database (read model tables: claim, evidence_link, tension, etc.). So the “meaning” is in the DB; the files are just content.

5. **scripts/ingest_chronicle_to_aura.py** — it verifies the .chronicle, imports it into the graph project (default or CHRONICLE_GRAPH_PROJECT), then runs sync to Neo4j (using NEO4J_URI, etc.).
