#!/usr/bin/env python3
"""
🧶 StateWeave Quick Start
===========================
Minimal example showing export → import → diff.
Copy this into your project to get started.

Run:
    pip install stateweave
    python examples/quickstart.py
"""

from stateweave import LangGraphAdapter, MCPAdapter, diff_payloads

# 1. Set up a LangGraph agent with some state
lg = LangGraphAdapter()
lg._agents["my-agent"] = {
    "messages": [
        {"type": "human", "content": "What's the weather?"},
        {"type": "ai", "content": "It's 72°F and sunny!"},
    ],
    "current_task": "weather_check",
}

# 2. Export state from LangGraph
payload = lg.export_state("my-agent")
print(f"Exported: {len(payload.cognitive_state.conversation_history)} messages")
print(f"Framework: {payload.source_framework}")

# 3. Import into MCP
mcp = MCPAdapter()
mcp.import_state(payload)
print("\nImported into MCP ✅")

# 4. Verify with re-export
mcp_payload = mcp.export_state("my-agent")
print(f"MCP has: {len(mcp_payload.cognitive_state.conversation_history)} messages")

# 5. Diff to see changes
diff = diff_payloads(payload, mcp_payload)
print(f"\nDiff: {len(diff.entries)} changes (framework tag + timestamps)")
print("\nDone! The agent's memories migrated successfully. 🧶")
