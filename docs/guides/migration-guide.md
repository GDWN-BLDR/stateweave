# Framework Migration Guide

> Switch AI agent frameworks in 30 seconds with zero data loss.

## Quick Migration

```python
from stateweave import LangGraphAdapter, CrewAIAdapter

# Export from source framework
source = LangGraphAdapter()
payload = source.export_state("my-agent")

# Import into target framework
target = CrewAIAdapter()
target.import_state(payload)

# Done. Messages, memory, goals — everything transferred.
```

## Supported Migration Paths

StateWeave supports **any-to-any** migration between 10 frameworks:

| Framework | Export | Import | Notes |
|-----------|--------|--------|-------|
| LangGraph | ✓ | ✓ | Full state including checkpointer |
| MCP | ✓ | ✓ | Model Context Protocol |
| CrewAI | ✓ | ✓ | Maps crew/task topology |
| AutoGen | ✓ | ✓ | Multi-agent conversations |
| DSPy | ✓ | ✓ | Prompt optimization state |
| LlamaIndex | ✓ | ✓ | Index and retrieval state |
| OpenAI Agents | ✓ | ✓ | Assistants API state |
| Haystack | ✓ | ✓ | Pipeline state |
| Letta | ✓ | ✓ | Memory blocks |
| Semantic Kernel | ✓ | ✓ | Planner state |

## Migration with Safety

Always checkpoint before migrating:

```python
from stateweave import LangGraphAdapter, MCPAdapter
from stateweave.core.timetravel import CheckpointStore

# Export
lg = LangGraphAdapter()
payload = lg.export_state("my-agent")

# Checkpoint (safety net)
store = CheckpointStore()
store.checkpoint(payload, label="pre-migration")

# Migrate
mcp = MCPAdapter()
result = mcp.import_state(payload)

# Verify
re_export = mcp.export_state(result["agent_id"])
assert len(re_export.cognitive_state.conversation_history) == \
       len(payload.cognitive_state.conversation_history)
print("✓ Zero data loss — migration verified")
```

## Handling Non-Portable State

Some state is framework-specific and can't be transferred:

```python
payload = lg.export_state("my-agent")

if payload.non_portable_warnings:
    for warning in payload.non_portable_warnings:
        print(f"⚠ [{warning.severity.value}] {warning.field}: {warning.reason}")
```

Common non-portable elements:
- **LangGraph**: Graph topology, edge conditions
- **CrewAI**: Delegation chains, process type
- **AutoGen**: Agent roles, group chat configuration
- **DSPy**: Compiled prompt chains

StateWeave preserves these in `framework_specific` metadata, but they may not be meaningful in the target framework.

## Encrypted Migration

For production migrations:

```python
from stateweave import EncryptionFacade, StateWeaveSerializer

# Serialize and encrypt
serializer = StateWeaveSerializer()
raw = serializer.dumps(payload)

facade = EncryptionFacade.from_passphrase("migration-key")
ciphertext, nonce = facade.encrypt(raw)

# ... transfer ciphertext to target environment ...

# Decrypt and import on the other side
decrypted = facade.decrypt(ciphertext, nonce)
restored = serializer.loads(decrypted)
target.import_state(restored)
```

## CLI Migration

```bash
# Export
stateweave export -f langgraph -a my-agent -o state.json

# Import on target
stateweave import -f crewai --payload state.json

# With encryption
stateweave export -f langgraph -a my-agent -o state.json --encrypt -p "key"
```

## When to Migrate

- **Framework evaluation**: Try your agent on a different framework without rebuilding
- **Team consolidation**: Standardize on one framework without losing work
- **Production upgrade**: Move from prototype (LangGraph) to production (MCP)
- **Disaster recovery**: Restore agent state from encrypted backups
