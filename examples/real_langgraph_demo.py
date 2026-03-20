#!/usr/bin/env python3
"""
Real LangGraph → StateWeave → MCP round-trip demo.

Run this to see StateWeave working with a REAL LangGraph graph.

    pip install stateweave langgraph langchain-core
    python examples/real_langgraph_demo.py
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.serializer import StateWeaveSerializer


def main():
    print("=" * 60)
    print("StateWeave — Real LangGraph Integration Demo")
    print("=" * 60)

    # Step 1: Build a real LangGraph graph with memory
    print("\n[1] Building real LangGraph StateGraph with MemorySaver...")

    def echo(state: MessagesState):
        last = state["messages"][-1]
        return {"messages": [AIMessage(content=f"Understood: {last.content}")]}

    builder = StateGraph(MessagesState)
    builder.add_node("echo", echo)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)

    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "demo-thread"}}
    print("    ✓ Graph compiled with MemorySaver checkpointer")

    # Step 2: Run real messages through the graph
    print("\n[2] Running messages through real LangGraph graph...")

    messages = [
        "I'm researching climate data for the Pacific Northwest",
        "Found 3 relevant datasets from NOAA",
        "Cross-referencing with local sensor readings",
    ]

    for msg in messages:
        graph.invoke({"messages": [HumanMessage(content=msg)]}, config)
        print(f"    → Human: {msg}")

    state = graph.get_state(config)
    msg_count = len(state.values["messages"])
    print(f"    ✓ LangGraph has {msg_count} messages accumulated")

    # Step 3: Export via StateWeave
    print("\n[3] Exporting state via StateWeave LangGraphAdapter...")

    adapter = LangGraphAdapter(checkpointer=graph.checkpointer, graph=graph)
    payload = adapter.export_state("demo-thread")

    print(f"    Source framework: {payload.source_framework}")
    print(f"    Messages captured: {len(payload.cognitive_state.conversation_history)}")
    print(f"    Working memory keys: {len(payload.cognitive_state.working_memory)}")
    print(f"    Non-portable warnings: {len(payload.non_portable_warnings)}")
    print("    ✓ Export complete")

    # Step 4: Serialize to JSON
    print("\n[4] Serializing payload to JSON...")

    serializer = StateWeaveSerializer()
    json_bytes = serializer.dumps(payload)
    print(f"    Payload size: {len(json_bytes):,} bytes")
    print("    ✓ Serialized to JSON (Pydantic validation passed)")

    # Step 5: Import into MCP adapter
    print("\n[5] Importing into MCP adapter...")

    mcp_adapter = MCPAdapter()
    result = mcp_adapter.import_state(payload)
    print(f"    Agent ID: {result['agent_id']}")
    print(f"    Import source: {result['import_source']}")
    print("    ✓ State imported into MCP")

    # Step 6: Verify round-trip
    print("\n[6] Verifying round-trip integrity...")

    mcp_payload = mcp_adapter.export_state(result["agent_id"])
    original = {m.content for m in payload.cognitive_state.conversation_history}
    roundtrip = {m.content for m in mcp_payload.cognitive_state.conversation_history}

    if original == roundtrip:
        print(f"    ✓ All {len(original)} messages survived the round-trip!")
    else:
        lost = original - roundtrip
        print(f"    ✗ Lost {len(lost)} messages in round-trip")

    # Show some content
    print("\n[7] Sample exported messages:")
    for msg in payload.cognitive_state.conversation_history[:4]:
        role = msg.role.value.upper()
        content = msg.content[:70]
        print(f"    [{role}] {content}")

    print("\n" + "=" * 60)
    print("Demo complete. Real LangGraph state successfully exported,")
    print("serialized, and imported into MCP adapter with full integrity.")
    print("=" * 60)


if __name__ == "__main__":
    main()
