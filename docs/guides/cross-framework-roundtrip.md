# Cross-Framework Roundtrip

Migrate agent state through multiple frameworks to prove portability.

## 4-Framework Chain

This example migrates state through all 4 Tier-1 frameworks: AutoGen → MCP → LangGraph → CrewAI. StateWeave supports 10 frameworks total.

```python
from stateweave import (
    AutoGenAdapter, MCPAdapter, LangGraphAdapter, CrewAIAdapter,
    MigrationEngine, StateWeaveSerializer, diff_payloads,
)

engine = MigrationEngine(serializer=StateWeaveSerializer(pretty=True))

# Step 1: Create agent in AutoGen
ag = AutoGenAdapter()
ag.register_agent("traveler", {
    "name": "research_assistant",
    "system_message": "You are a research assistant.",
    "chat_messages": {
        "user": [
            {"role": "user", "content": "What are the top AI frameworks?"},
            {"role": "assistant", "content": "LangGraph, CrewAI, AutoGen"},
        ],
    },
})

result_ag = engine.export_state(ag, "traveler", encrypt=False)

# Step 2: AutoGen → MCP
mcp = MCPAdapter()
engine.import_state(mcp, payload=result_ag.payload)

# Step 3: MCP → LangGraph
lg = LangGraphAdapter()
result_mcp = engine.export_state(mcp, "traveler", encrypt=False)
engine.import_state(lg, payload=result_mcp.payload)

# Step 4: LangGraph → CrewAI
result_lg = engine.export_state(lg, "traveler", encrypt=False)
crew = CrewAIAdapter()
engine.import_state(crew, payload=result_lg.payload, crew_id="final")

# Step 5: Verify
result_crew = engine.export_state(crew, "final", encrypt=False)
diff = diff_payloads(result_ag.payload, result_crew.payload)
print(f"Changes after 4 hops: {len(diff.entries)}")
```

Run the full example:

```bash
python examples/four_way_migration.py
```
