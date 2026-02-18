# Quiz 08: The Chronicle CLI

**Lesson:** [08-cli.md](../08-cli.md)

Answer these after reading the lesson and the CLI main. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. How do you **initialize** a new Chronicle project from the command line? (Exact subcommand and typical usage.)

2. What does **chronicle quickstart-rag** do? When would you use **--path** or **--text**?

3. What is the difference between **chronicle verify** and **chronicle verify-chronicle**?

4. Which subcommand do you use to **push** the project’s read model to Neo4j? What environment variables are required?

5. Where is the CLI **entry point** defined? (File and symbol.)

6. How do you get the **defensibility scorecard** for a specific claim from the CLI? (Subcommand and required args.)

7. How do you **attribute** a CLI write (e.g. create-investigation) to yourself so the ledger records you as the actor?

---

## Answer key

1. **chronicle init &lt;path&gt;** — e.g. `chronicle init /path/to/project`. This creates the project directory with chronicle.db and schema.

2. **chronicle quickstart-rag** runs a minimal RAG-style flow: creates a (temp or given) project, an investigation, ingests sample or custom text as evidence, proposes a claim, links support, and prints defensibility. Use **--path** to keep the project (e.g. for later inspection); use **--text /path/to/file.txt** to use your own document as evidence instead of the default sample. See docs/rag-in-5-minutes.md.

3. **chronicle verify** runs the **project invariant suite** on a **project directory** (checks project state, schema, evidence files). **chronicle verify-chronicle** runs the **.chronicle file verifier** on a **ZIP file** (manifest, DB schema, evidence hashes). Same logic as the standalone **chronicle-verify** entry point.

4. **chronicle neo4j-sync --path /path/to/project**. Required: **NEO4J_URI** and **NEO4J_PASSWORD** (and optionally NEO4J_USER). Often set via .env in the repo root.

5. In **pyproject.toml**: **chronicle = chronicle.cli.main:main** (the **main** function in **chronicle/cli/main.py**).

6. **chronicle get-defensibility &lt;claim_uid&gt; --path /path/to/project** (claim_uid is a positional argument). Returns the defensibility scorecard for that claim.

7. Set **CHRONICLE_ACTOR_ID** (and optionally **CHRONICLE_ACTOR_TYPE**) in the environment, or pass **--actor-id** and **--actor-type** on the command (e.g. `chronicle --actor-id jane_doe create-investigation "My run" --path /path/to/project`). See docs/human-in-the-loop-and-attestation.md.
