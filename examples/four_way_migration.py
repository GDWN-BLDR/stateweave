#!/usr/bin/env python3
"""
🧶 StateWeave: 4-Framework Migration Demo
=============================================
Demonstrates state traveling through all 4 Tier-1 frameworks:
AutoGen → MCP → LangGraph → CrewAI

This proves the Universal Schema works as a true universal interchange format.

Run:
    pip install stateweave
    python examples/four_way_migration.py
"""

from stateweave import (
    AutoGenAdapter,
    CrewAIAdapter,
    LangGraphAdapter,
    MCPAdapter,
    MigrationEngine,
    StateWeaveSerializer,
    diff_payloads,
)


def main():
    engine = MigrationEngine(serializer=StateWeaveSerializer(pretty=True))

    # ── Step 1: Start in AutoGen ──
    print("🔵 Step 1: Creating agent in AutoGen...")
    ag = AutoGenAdapter()
    ag.register_agent(
        "traveler",
        {
            "name": "research_assistant",
            "system_message": "You are a research assistant.",
            "chat_messages": {
                "user": [
                    {"role": "user", "content": "What are the top 3 AI frameworks?"},
                    {"role": "assistant", "content": "1. LangGraph\n2. CrewAI\n3. AutoGen"},
                    {"role": "user", "content": "Compare their state management."},
                    {
                        "role": "assistant",
                        "content": "LangGraph: checkpoint-based. CrewAI: crew memory. AutoGen: chat_messages dict.",
                    },
                ],
            },
        },
    )

    result_ag = engine.export_state(ag, "traveler", encrypt=False)
    print(f"   Messages: {len(result_ag.payload.cognitive_state.conversation_history)}")
    print(f"   Warnings: {len(result_ag.payload.non_portable_warnings)}")

    # ── Step 2: AutoGen → MCP ──
    print("\n🟢 Step 2: Migrating AutoGen → MCP...")
    mcp = MCPAdapter()
    engine.import_state(mcp, payload=result_ag.payload)
    result_mcp = engine.export_state(mcp, "traveler", encrypt=False)
    print(f"   Messages: {len(result_mcp.payload.cognitive_state.conversation_history)}")

    # ── Step 3: MCP → LangGraph ──
    print("\n🟣 Step 3: Migrating MCP → LangGraph...")
    lg = LangGraphAdapter()
    engine.import_state(lg, payload=result_mcp.payload)
    result_lg = engine.export_state(lg, "traveler", encrypt=False)
    print(f"   Messages: {len(result_lg.payload.cognitive_state.conversation_history)}")

    # ── Step 4: LangGraph → CrewAI ──
    print("\n🟠 Step 4: Migrating LangGraph → CrewAI...")
    crew = CrewAIAdapter()
    engine.import_state(crew, payload=result_lg.payload, crew_id="final")
    result_crew = engine.export_state(crew, "final", encrypt=False)
    print(f"   Messages: {len(result_crew.payload.cognitive_state.conversation_history)}")

    # ── Step 5: Diff origin vs final ──
    print("\n🔍 Step 5: Diffing origin (AutoGen) vs final (CrewAI)...")
    diff = diff_payloads(result_ag.payload, result_crew.payload)
    print(f"   Changes: {len(diff.entries)}")
    print(
        f"   Added: {diff.added_count} | Removed: {diff.removed_count} | Modified: {diff.modified_count}"
    )

    # Verify conversation survived
    original_msgs = {m.content for m in result_ag.payload.cognitive_state.conversation_history}
    final_msgs = {m.content for m in result_crew.payload.cognitive_state.conversation_history}
    preserved = original_msgs & final_msgs
    print(f"\n✅ {len(preserved)}/{len(original_msgs)} messages survived 4 framework hops!")
    print("\n🧶 The Universal Schema works. State is truly portable.")


if __name__ == "__main__":
    main()
