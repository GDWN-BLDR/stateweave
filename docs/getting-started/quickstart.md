# Quick Start

Get started with StateWeave in under 5 minutes.

## Install

```bash
pip install stateweave
```

## Export Agent State

```python
from stateweave import LangGraphAdapter, StateWeaveSerializer

# Create adapter (or pass a real checkpointer)
adapter = LangGraphAdapter()
adapter._agents["my-agent"] = {
    "messages": [
        {"type": "human", "content": "What's the weather?"},
        {"type": "ai", "content": "It's 72°F and sunny!"},
    ],
    "current_task": "weather_check",
}

# Export
payload = adapter.export_state("my-agent")
print(f"Exported {len(payload.cognitive_state.conversation_history)} messages")
```

## Import Into Another Framework

```python
from stateweave import MCPAdapter

mcp = MCPAdapter()
mcp.import_state(payload)

# Agent resumes with full context intact
```

## Diff Two States

```python
from stateweave import diff_payloads

diff = diff_payloads(state_before, state_after)
print(diff.to_report())
```

## What's Next?

- [Encrypted Migration](../guides/encrypted-migration.md) — add AES-256-GCM encryption
- [Cross-Framework Roundtrip](../guides/cross-framework-roundtrip.md) — migrate through 10 frameworks
- [MCP Server Setup](../guides/mcp-server.md) — use StateWeave from any MCP client
- [API Reference](../api/schema.md) — full schema documentation
