#!/usr/bin/env python3
"""
🧶 StateWeave: Real LangGraph Integration Example
====================================================
Demonstrates StateWeave with a real LangGraph-style state structure,
showing how actual checkpointer data would export and import.

This example uses realistic LangGraph checkpoint data structures
to show what a real integration looks like.

Run:
    pip install stateweave
    python examples/real_langgraph_integration.py
"""

from stateweave import (
    CrewAIAdapter,
    EncryptionFacade,
    LangGraphAdapter,
    MigrationEngine,
    StateWeaveSerializer,
    diff_payloads,
)


def main():
    # ── Simulate real LangGraph checkpoint data ──
    # In production, this comes from SqliteSaver or PostgresSaver
    print("🔵 Creating realistic LangGraph agent state...\n")

    lg = LangGraphAdapter()

    # This mirrors real LangGraph checkpoint structure
    lg._agents["financial-analyst"] = {
        # Messages in LangGraph format (BaseMessage-compatible)
        "messages": [
            {
                "type": "human",
                "content": "Analyze AAPL's Q3 2025 earnings report.",
                "id": "msg_001",
            },
            {
                "type": "ai",
                "content": (
                    "Apple reported Q3 2025 revenue of $94.8B, up 8% YoY. "
                    "Key highlights:\n"
                    "1. Services revenue hit $24.2B (record)\n"
                    "2. iPhone revenue $46.1B (+5%)\n"
                    "3. Greater China revenue improved to $15.3B\n"
                    "4. Gross margin expanded to 46.3%"
                ),
                "id": "msg_002",
                "tool_calls": [],
            },
            {
                "type": "human",
                "content": "What are the key risks going forward?",
                "id": "msg_003",
            },
            {
                "type": "ai",
                "content": (
                    "Key risks for AAPL:\n"
                    "1. EU DMA compliance costs (~$2B estimated annual impact)\n"
                    "2. China market uncertainty (Huawei competition)\n"
                    "3. AI monetization timeline unclear\n"
                    "4. App Store regulatory pressure globally"
                ),
                "id": "msg_004",
            },
        ],
        # Working state
        "current_analysis": {
            "ticker": "AAPL",
            "recommendation": "HOLD",
            "price_target": 245.00,
            "confidence": 0.87,
        },
        # Tool results (real LangGraph caches these)
        "tool_outputs": {
            "bloomberg_lookup": {"pe_ratio": 31.4, "market_cap": "3.4T"},
            "sec_filing": {"filing_type": "10-Q", "date": "2025-08-01"},
        },
        # LangGraph-specific internals (non-portable)
        "__channel_versions__": {"messages": 4, "current_analysis": 1},
        "__pregel_tasks__": {"analyze": "completed", "summarize": "pending"},
    }

    # ── Export from LangGraph ──
    print("📤 Exporting from LangGraph...")
    payload = lg.export_state("financial-analyst")

    print(f"   Messages: {len(payload.cognitive_state.conversation_history)}")
    print(f"   Working memory keys: {len(payload.cognitive_state.working_memory)}")
    print(f"   Tool cache entries: {len(payload.cognitive_state.tool_results_cache)}")
    print(f"   Non-portable warnings: {len(payload.non_portable_warnings)}")

    # Show non-portable warnings (the honest part)
    if payload.non_portable_warnings:
        print("\n   ⚠️  Non-portable elements (explicitly documented):")
        for w in payload.non_portable_warnings:
            print(f"      [{w.severity}] {w.field}: {w.reason}")

    # ── Encrypt for transport ──
    print("\n🔒 Encrypting for secure transport...")
    key = EncryptionFacade.generate_key()
    engine = MigrationEngine(
        serializer=StateWeaveSerializer(),
        encryption=EncryptionFacade(key),
    )

    export_result = engine.export_state(lg, "financial-analyst", encrypt=True)
    print(f"   Encrypted: {len(export_result.encrypted_data):,} bytes")

    # ── Import into CrewAI ──
    print("\n📥 Importing into CrewAI...")
    crew = CrewAIAdapter()
    engine.import_state(
        crew,
        encrypted_data=export_result.encrypted_data,
        nonce=export_result.nonce,
        crew_id="research-crew",
    )

    # ── Verify the migration ──
    print("\n✅ Verifying migration integrity...")
    crew_payload = crew.export_state("research-crew")

    original_msgs = len(payload.cognitive_state.conversation_history)
    final_msgs = len(crew_payload.cognitive_state.conversation_history)

    print(f"   Messages: {final_msgs}/{original_msgs} preserved")
    print(f"   Working memory: {len(crew_payload.cognitive_state.working_memory)} keys")
    print(f"   Source: {crew_payload.source_framework}")

    # ── Diff to see what changed ──
    print("\n🔍 Diffing original vs imported...")
    diff = diff_payloads(payload, crew_payload)
    print(f"   Changes: {len(diff.entries)}")
    print(
        f"   Added: {diff.added_count} | Removed: {diff.removed_count} | Modified: {diff.modified_count}"
    )

    print("\n🧶 Real-world migration complete: LangGraph → (encrypted) → CrewAI")
    print("   Agent's analysis, messages, and tool results survived the journey.")


if __name__ == "__main__":
    main()
