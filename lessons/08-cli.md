# Lesson 08: The Chronicle CLI

**Objectives:** You’ll know how the `chronicle` CLI is organized, what the main subcommands do (init, verify-chronicle, neo4j-sync, export, defensibility, etc.), and where to find the implementation.

**Key files:**

- [chronicle/cli/main.py](../chronicle/cli/main.py) — CLI entry point and subparsers
- [pyproject.toml](../pyproject.toml) — console script entry: `chronicle = chronicle.cli.main:main`
- [docs/aura-graph-pipeline.md](../docs/aura-graph-pipeline.md) — Neo4j sync and ingest runbook

---

## How to run the CLI

After **`pip install -e .`** (and with the venv activated if you use one), the command is:

```bash
chronicle --help
chronicle init --help
chronicle verify-chronicle --help
chronicle neo4j-sync --path /path/to/project
```

The entry point is defined in **pyproject.toml**: `chronicle = chronicle.cli.main:main`. So `main()` in **chronicle/cli/main.py** parses arguments and dispatches to the right handler.

## Main subcommands

Open **chronicle/cli/main.py** and scan the **subparsers** (e.g. around lines 540–890).

| Subcommand | Purpose |
|------------|---------|
| **quickstart-rag** | One-command RAG demo: create temp project, investigation, ingest sample text, propose claim, link support, print defensibility. Use `--path` to keep the project; `--text` for your own file. See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md). |
| **init** | Initialize a Chronicle project directory (creates chronicle.db, schema). |
| **create-investigation** | Create an investigation (title, etc.) in the project. |
| **ingest-evidence** | Ingest a file as evidence into an investigation. |
| **export** | Export an investigation to a .chronicle file (ZIP). |
| **export-minimal** | Export a minimal .chronicle containing only one claim and its evidence/links/tensions. |
| **import** | Import a .chronicle file into the project. |
| **get-defensibility** | Get the defensibility scorecard for a claim (by claim_uid). |
| **reasoning-trail** | Get the reasoning trail (events that built or modified the claim). |
| **reasoning-brief** | Generate the reasoning brief (human-readable summary) for a claim. |
| **verify** | Run the **project** invariant suite (different from verify-chronicle: checks project state). |
| **verify-chronicle** | Run the **.chronicle file** verifier (manifest, schema, evidence hashes). Same as the standalone `chronicle-verify` entry point. |
| **neo4j-sync** | Sync the project’s read model to Neo4j (requires NEO4J_URI, NEO4J_PASSWORD). |
| **neo4j** (subcommands) | Neo4j export (e.g. CSV) and related. |
| **policy** | List, export, or import policy profiles. |

So the CLI is a **wrapper** around the same session and commands used by the scorer and scripts: init creates the project, then other commands use ChronicleSession (or the verifier, or Neo4j sync) under the hood.

## Attribution (actor identity)

Write commands (create-investigation, ingest-evidence, set-tier, quickstart-rag) record **who** did the action. You can set your identity so the ledger attributes writes to you:

- **Environment:** Set **CHRONICLE_ACTOR_ID** and optionally **CHRONICLE_ACTOR_TYPE** (e.g. `human`, `tool`). Any write command in that shell will use them.
- **Flags:** Pass **--actor-id** and **--actor-type** on the same run (e.g. `chronicle --actor-id jane_doe create-investigation "My run" --path /path/to/project`). Flags override env.

Scripts that use the session (e.g. **scripts/ingest_transcript_csv.py**) also respect **CHRONICLE_ACTOR_ID** for the curator. See [docs/human-in-the-loop-and-attestation.md](../docs/human-in-the-loop-and-attestation.md).

## verify vs verify-chronicle

- **chronicle verify** — Operates on a **project directory**. Runs the project invariant suite (e.g. schema consistency, evidence files present). Implemented in **chronicle/verify.py**.
- **chronicle verify-chronicle** — Operates on a **.chronicle file** (ZIP). Runs the standalone verifier (manifest, DB schema, evidence hashes). Same logic as **chronicle-verify** (tools/verify_chronicle). Use this when someone hands you a .chronicle and you want to check it without opening the DB.

## Try it

1. Run **chronicle --help** and list all top-level subcommands.
2. Run **chronicle quickstart-rag** (no path: uses a temp dir). You should see project path, investigation UID, claim UID, and defensibility. Then try **chronicle quickstart-rag --path /tmp/my_rag** to keep the project.
3. Run **chronicle init /tmp/test_chronicle** (or a temp path), then **chronicle create-investigation --path /tmp/test_chronicle --title "Test"**. Confirm the project has an investigation (e.g. list it or run defensibility after adding a claim via a script).
4. From the repo, run **chronicle verify-chronicle path/to/sample.chronicle** (generate a sample first with scripts/generate_sample_chronicle.py if needed).

## Summary

- The **chronicle** CLI is implemented in **chronicle/cli/main.py**; entry point in pyproject.toml.
- **quickstart-rag** gives a one-command RAG flow (project, investigation, evidence, claim, defensibility); **init**, **create-investigation**, **ingest-evidence**, **export**, **import**, **get-defensibility**, **reasoning-trail**, **reasoning-brief**, **verify**, **verify-chronicle**, **neo4j-sync**, **policy** are the other main subcommands.
- Set **CHRONICLE_ACTOR_ID** (or **--actor-id**) so write commands are attributed to you; see human-in-the-loop doc.
- **verify** = project invariants; **verify-chronicle** = .chronicle file verifier (same as chronicle-verify).

**Quiz:** [quizzes/quiz-08-cli.md](quizzes/quiz-08-cli.md)
