# Lesson 08: The Chronicle CLI

Objectives: You’ll know how the `chronicle` CLI is organized, what the main subcommands do (init, verify-chronicle, neo4j-export, neo4j-sync, export, defensibility, etc.), how the companion `chronicle-mcp` entry point fits in, and where to find the implementation.

**Key files:**

- [chronicle/cli/main.py](../chronicle/cli/main.py) — CLI entry point and subparsers
- [chronicle/cli/project_commands.py](../chronicle/cli/project_commands.py) — project/investigation command implementations extracted from `main.py`
- [pyproject.toml](../pyproject.toml) — console script entries: `chronicle = chronicle.cli.main:main`, `chronicle-mcp = chronicle.mcp.server:main`
- [docs/aura-graph-pipeline.md](../docs/aura-graph-pipeline.md) — Neo4j sync and ingest runbook
- [docs/mcp.md](../docs/mcp.md) — MCP server usage and transports

---

## How to run the CLI

After `pip install -e .` (and with the venv activated if you use one), the command is:

```bash
chronicle --help
chronicle init --help
chronicle verify-chronicle --help
chronicle neo4j-export --path /path/to/project --output /tmp/neo4j_import
chronicle neo4j-sync --path /path/to/project
```

The `chronicle` entry point is defined in pyproject.toml: `chronicle = chronicle.cli.main:main`. So `main()` in chronicle/cli/main.py parses arguments and dispatches to command handlers; several project-oriented handlers are implemented in chronicle/cli/project_commands.py.

Chronicle also ships a companion command for agent tooling, `chronicle-mcp`, defined as `chronicle.mcp.server:main` (optional `.[mcp]` extra). It is not a subcommand of `chronicle`; it is a separate entry point for MCP protocol transport.

## Main subcommands

Open chronicle/cli/main.py and scan the subparsers. Then open chronicle/cli/project_commands.py to see the extracted implementations for project/investigation operations.

| Subcommand | Purpose |
|------------|---------|
| quickstart-rag | One-command RAG demo: create temp project, investigation, ingest sample text, propose claim, link support, print defensibility. Use `--path` to keep the project; `--text` for your own file. See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md). |
| init | Initialize a Chronicle project directory (creates chronicle.db, schema). |
| create-investigation | Create an investigation (title, etc.) in the project. |
| ingest-evidence | Ingest a file as evidence into an investigation. |
| export | Export an investigation to a .chronicle file (ZIP). |
| export-minimal | Export a minimal .chronicle containing only one claim and its evidence/links/tensions. |
| import | Import a .chronicle file into the project. |
| get-defensibility | Get the defensibility scorecard for a claim (by claim_uid). |
| reasoning-trail | Get the reasoning trail (events that built or modified the claim). |
| reasoning-brief | Generate the reasoning brief (human-readable summary) for a claim. |
| verify | Run the project invariant suite (different from verify-chronicle: checks project state). |
| verify-chronicle | Run the .chronicle file verifier (manifest, schema, evidence hashes). Same as the standalone `chronicle-verify` entry point. |
| neo4j-export | Export project read-model CSVs for Neo4j rebuild scripts; supports `--report` and `--progress`. |
| neo4j-sync | Sync the project’s read model to Neo4j (requires NEO4J_URI, NEO4J_PASSWORD); supports hardening flags plus `--report` and `--progress`. |
| policy | List, export, or import policy profiles. |

So the CLI is a wrapper around the same session and commands used by the scorer and scripts: init creates the project, then other commands use ChronicleSession (or the verifier, or Neo4j sync) under the hood.

## Attribution (actor identity)

Write commands (create-investigation, ingest-evidence, set-tier, quickstart-rag) record who did the action. You can set your identity so the ledger attributes writes to you:

- Environment: Set CHRONICLE_ACTOR_ID and optionally CHRONICLE_ACTOR_TYPE (e.g. `human`, `tool`). Any write command in that shell will use them.
- Flags: Pass --actor-id and --actor-type on the same run (e.g. `chronicle --actor-id jane_doe create-investigation "My run" --path /path/to/project`). Flags override env.

Scripts that use the session (e.g. scripts/ingest_transcript_csv.py) also respect CHRONICLE_ACTOR_ID for the curator. See [docs/human-in-the-loop-and-attestation.md](../docs/human-in-the-loop-and-attestation.md).

## verify vs verify-chronicle

- **chronicle verify** — Operates on a project directory. Runs the project invariant suite (e.g. schema consistency, evidence files present). Implemented in chronicle/verify.py.
- **chronicle verify-chronicle** — Operates on a .chronicle file (ZIP). Runs the standalone verifier (manifest, DB schema, evidence hashes). Same logic as chronicle-verify (tools/verify_chronicle). Use this when someone hands you a .chronicle and you want to check it without opening the DB.

## chronicle vs chronicle-mcp

- **chronicle** is an operator/developer CLI (explicit commands typed by a human or script).
- **chronicle-mcp** is a protocol server for assistant tool-calling (tools invoked by an MCP client).

Both share the same Chronicle core/session behavior; they differ in invocation model and integration boundary.

## Try it

1. Run chronicle --help and list all top-level subcommands.
2. Run chronicle quickstart-rag (no path: uses a temp dir). You should see project path, investigation UID, claim UID, and defensibility. Then try chronicle quickstart-rag --path /tmp/my_rag to keep the project.
3. Run chronicle init /tmp/test_chronicle (or a temp path), then chronicle create-investigation --path /tmp/test_chronicle --title "Test". Confirm the project has an investigation (e.g. list it or run defensibility after adding a claim via a script).
4. From the repo, run chronicle verify-chronicle path/to/sample.chronicle (generate a sample first with scripts/generate_sample_chronicle.py if needed).
5. (Optional) Install `.[mcp]` and run `chronicle-mcp --project-path /tmp/chronicle_cli_mcp`. Confirm `--transport` accepts `stdio`, `sse`, or `streamable-http`.

## Summary

- The chronicle CLI entry point and argument parsing live in chronicle/cli/main.py; several command implementations are factored into chronicle/cli/project_commands.py.
- quickstart-rag gives a one-command RAG flow (project, investigation, evidence, claim, defensibility); init, create-investigation, ingest-evidence, export, import, get-defensibility, reasoning-trail, reasoning-brief, verify, verify-chronicle, neo4j-export, neo4j-sync, policy are the other main subcommands.
- `chronicle-mcp` is a separate console entry point for assistant tool-calling over MCP transports.
- Set CHRONICLE_ACTOR_ID (or --actor-id) so write commands are attributed to you; see human-in-the-loop doc.
- verify = project invariants; verify-chronicle = .chronicle file verifier (same as chronicle-verify).

← Previous: [Lesson 07: Integrations and scripts](07-integrations-and-scripts.md) | Index: [Lessons](README.md) | Next →: [Lesson 09: Epistemic tools](09-epistemic-tools.md)

Quiz: [quizzes/quiz-08-cli.md](quizzes/quiz-08-cli.md)
