# MCP integration

Chronicle includes an MCP server so AI assistants can call Chronicle tools directly (investigations, evidence, claims, links, defensibility, export).

## Install

```bash
pip install "chronicle-standard[mcp]"
```

Or from source:

```bash
pip install -e ".[mcp]"
```

## Run server

Default transport is `stdio` (best for desktop/agent integrations):

```bash
chronicle-mcp --project-path /path/to/chronicle_project
```

HTTP transports are also supported:

```bash
chronicle-mcp --project-path /path/to/chronicle_project --transport streamable-http --host 127.0.0.1 --port 8000
```

The project directory is auto-initialized if it does not exist yet.

## Tools exposed

- `chronicle_create_investigation`
- `chronicle_list_investigations`
- `chronicle_ingest_evidence_text`
- `chronicle_propose_claim`
- `chronicle_list_claims`
- `chronicle_link_support`
- `chronicle_link_challenge`
- `chronicle_get_defensibility`
- `chronicle_get_reasoning_brief`
- `chronicle_export_investigation`

## Example MCP client config

```json
{
  "mcpServers": {
    "chronicle": {
      "command": "chronicle-mcp",
      "args": ["--project-path", "/absolute/path/to/chronicle_project"]
    }
  }
}
```

## Security notes

- Treat this as a trusted local integration surface.
- For network transports (`sse` / `streamable-http`), put Chronicle behind your normal auth/network controls.

