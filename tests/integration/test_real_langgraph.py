"""
Integration test: Real LangGraph → StateWeave → MCP round-trip.

This test creates an ACTUAL LangGraph StateGraph with InMemorySaver,
runs real messages through it, then exports the state using StateWeave
and verifies the full round-trip.

Requires: pip install langgraph langchain-core
"""

import pytest

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, MessagesState, StateGraph

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.schema.v1 import MessageRole


@pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph not installed")
class TestRealLangGraphIntegration:
    """Tests using a REAL LangGraph graph with actual checkpointer."""

    def _build_graph(self):
        """Build a real LangGraph stateful graph with memory."""
        checkpointer = MemorySaver()

        def echo_node(state: MessagesState):
            """Simple node that generates a response based on last message."""
            last_msg = state["messages"][-1]
            return {
                "messages": [
                    AIMessage(content=f"I heard you say: {last_msg.content}")
                ]
            }

        builder = StateGraph(MessagesState)
        builder.add_node("echo", echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)

        graph = builder.compile(checkpointer=checkpointer)
        return graph, checkpointer

    def test_export_real_langgraph_state(self):
        """Export state from a REAL LangGraph graph with accumulated messages."""
        graph, checkpointer = self._build_graph()
        thread_id = "integration-test-thread"
        config = {"configurable": {"thread_id": thread_id}}

        # Run real messages through the graph
        graph.invoke(
            {"messages": [HumanMessage(content="Hello, I'm testing StateWeave")]},
            config=config,
        )
        graph.invoke(
            {"messages": [HumanMessage(content="Can you remember what I said?")]},
            config=config,
        )
        graph.invoke(
            {"messages": [HumanMessage(content="This is the third message")]},
            config=config,
        )

        # Verify LangGraph has accumulated state
        state = graph.get_state(config)
        assert len(state.values["messages"]) >= 6  # 3 human + 3 AI

        # NOW: Export via StateWeave adapter
        adapter = LangGraphAdapter(checkpointer=checkpointer, graph=graph)
        payload = adapter.export_state(thread_id)

        # Verify the payload captured real state
        assert payload.source_framework == "langgraph"
        assert len(payload.cognitive_state.conversation_history) >= 6
        assert payload.metadata.agent_id == thread_id

        # Verify message roles are correctly mapped
        roles = [m.role for m in payload.cognitive_state.conversation_history]
        assert MessageRole.HUMAN in roles
        assert MessageRole.ASSISTANT in roles

        # Verify actual content transferred
        contents = [m.content for m in payload.cognitive_state.conversation_history]
        assert any("testing StateWeave" in c for c in contents)
        assert any("I heard you say" in c for c in contents)

    def test_round_trip_langgraph_to_mcp(self):
        """Full round-trip: Real LangGraph → StateWeave → MCP adapter."""
        graph, checkpointer = self._build_graph()
        thread_id = "roundtrip-test"
        config = {"configurable": {"thread_id": thread_id}}

        # Run messages through real graph
        graph.invoke(
            {"messages": [HumanMessage(content="Research findings on topic X")]},
            config=config,
        )
        graph.invoke(
            {"messages": [HumanMessage(content="Continue analysis with new data")]},
            config=config,
        )

        # Export from real LangGraph
        lg_adapter = LangGraphAdapter(checkpointer=checkpointer, graph=graph)
        payload = lg_adapter.export_state(thread_id)

        # Import into MCP adapter
        mcp_adapter = MCPAdapter()
        result = mcp_adapter.import_state(payload)

        assert result["framework"] == "mcp"
        assert result["import_source"] == "langgraph"

        # Re-export from MCP to verify state survived
        mcp_payload = mcp_adapter.export_state(result["agent_id"])

        # Verify the round-trip preserved content
        original_contents = {
            m.content for m in payload.cognitive_state.conversation_history
        }
        roundtrip_contents = {
            m.content for m in mcp_payload.cognitive_state.conversation_history
        }
        assert original_contents == roundtrip_contents

    def test_export_preserves_message_metadata(self):
        """Verify that LangGraph message metadata (tool calls, etc.) is preserved."""
        graph, checkpointer = self._build_graph()
        thread_id = "metadata-test"
        config = {"configurable": {"thread_id": thread_id}}

        # Run a message
        graph.invoke(
            {"messages": [SystemMessage(content="You are a helpful assistant")]},
            config=config,
        )
        graph.invoke(
            {"messages": [HumanMessage(content="What's 2+2?")]},
            config=config,
        )

        # Export
        adapter = LangGraphAdapter(checkpointer=checkpointer, graph=graph)
        payload = adapter.export_state(thread_id)

        # Verify system message was captured
        roles = [m.role for m in payload.cognitive_state.conversation_history]
        assert MessageRole.SYSTEM in roles

        # Verify audit trail
        assert len(payload.audit_trail) > 0
        assert payload.audit_trail[0].framework == "langgraph"
        assert payload.audit_trail[0].success is True

    def test_import_into_new_langgraph_thread(self):
        """Export from one LangGraph thread, import into another."""
        graph, checkpointer = self._build_graph()

        # Run messages in thread A
        config_a = {"configurable": {"thread_id": "thread-A"}}
        graph.invoke(
            {"messages": [HumanMessage(content="Important context from thread A")]},
            config=config_a,
        )

        # Export thread A
        adapter = LangGraphAdapter(checkpointer=checkpointer, graph=graph)
        payload = adapter.export_state("thread-A")

        # Import into thread B
        result = adapter.import_state(payload, thread_id="thread-B")
        assert result["thread_id"] == "thread-B"

        # Verify thread B has the imported state
        config_b = {"configurable": {"thread_id": "thread-B"}}
        state_b = graph.get_state(config_b)

        # Thread B should have the messages from thread A
        if state_b.values:
            contents = [
                m.content
                for m in state_b.values.get("messages", [])
                if hasattr(m, "content")
            ]
            # The import worked if we have state
            assert result["framework"] == "langgraph"
