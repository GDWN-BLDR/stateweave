# MCP Server Setup

StateWeave ships as a native MCP Server. Any MCP-compatible AI assistant (Claude, Cursor, etc.) can use it directly.

## Configuration

Add to your MCP client config (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "stateweave": {
      "command": "python3",
      "args": ["-m", "stateweave.mcp_server"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `export_agent_state` | Export cognitive state from any framework |
| `import_agent_state` | Import into target framework with validation |
| `diff_agent_states` | Detailed change report between two states |

## Available Resources

| Resource | URI |
|----------|-----|
| Universal Schema spec | `stateweave://schemas/v1` |
| Migration history | `stateweave://migrations/history` |
| Agent snapshot | `stateweave://agents/{id}/snapshot` |

## Prompt Templates

| Prompt | Use Case |
|--------|----------|
| `backup_before_risky_operation` | Agent self-requests backup before risky ops |
| `migration_guide` | Step-by-step framework migration template |

## Running Standalone

```bash
# Via stdio (typical MCP usage)
python -m stateweave.mcp_server

# Via the installed CLI
stateweave-mcp-server
```

## Docker Deployment

```bash
docker build -t stateweave .
docker run -it stateweave
```

Or with docker-compose:

```bash
docker compose up stateweave-mcp
```
