"""
Integration Tests: MCP → LangGraph Migration
===============================================
Full migration pipeline from MCP to LangGraph.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import (
    MessageRole,
)


class TestMCPToLangGraphMigration:
    @pytest.fixture
    def mcp_adapter(self):
        adapter = MCPAdapter()
        adapter.register_agent(
            "mcp-agent-1",
            {
                "messages": [
                    {"role": "user", "content": "Find me some research papers on AI."},
                    {"role": "assistant", "content": "I'll search for that."},
                    {
                        "role": "tool",
                        "content": "Found 5 papers",
                        "name": "search",
                        "tool_call_id": "tc_1",
                    },
                    {"role": "assistant", "content": "Here are 5 papers on AI..."},
                ],
                "tool_calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "AI research papers 2026"},
                        "result": {"count": 5, "urls": ["https://arxiv.org/1"]},
                        "success": True,
                    },
                ],
                "resources": {
                    "papers://recent": {"count": 5},
                },
                "servers": ["mcp-server-search"],
            },
        )
        return adapter

    @pytest.fixture
    def langgraph_adapter(self):
        return LangGraphAdapter()

    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    def test_basic_migration(self, mcp_adapter, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        # Export from MCP
        export_result = engine.export_state(
            adapter=mcp_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )
        assert export_result.success

        # Import to LangGraph
        import_result = engine.import_state(
            adapter=langgraph_adapter,
            payload=export_result.payload,
        )
        assert import_result.success

    def test_conversation_preserved(self, mcp_adapter, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=mcp_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )

        msgs = export_result.payload.cognitive_state.conversation_history
        assert len(msgs) == 4
        assert msgs[0].role == MessageRole.HUMAN
        assert msgs[1].role == MessageRole.ASSISTANT

        # Import and re-export
        engine.import_state(
            adapter=langgraph_adapter,
            payload=export_result.payload,
        )
        re_exported = langgraph_adapter.export_state("mcp-agent-1")
        assert len(re_exported.cognitive_state.conversation_history) == 4

    def test_tool_results_transferred(self, mcp_adapter, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=mcp_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )

        tool_cache = export_result.payload.cognitive_state.tool_results_cache
        assert "web_search" in tool_cache

    def test_framework_tag_changes(self, mcp_adapter, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=mcp_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )
        assert export_result.payload.source_framework == "mcp"

        # After import to langgraph, a re-export should show langgraph
        engine.import_state(
            adapter=langgraph_adapter,
            payload=export_result.payload,
        )
        re_exported = langgraph_adapter.export_state("mcp-agent-1")
        assert re_exported.source_framework == "langgraph"

    def test_bidirectional_migration(self, mcp_adapter, langgraph_adapter, serializer):
        """Test MCP → LangGraph → MCP roundtrip."""
        engine = MigrationEngine(serializer=serializer)

        # Step 1: MCP → Universal Schema
        export1 = engine.export_state(
            adapter=mcp_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )
        assert export1.success
        original_msgs = len(export1.payload.cognitive_state.conversation_history)

        # Step 2: Universal Schema → LangGraph
        import1 = engine.import_state(
            adapter=langgraph_adapter,
            payload=export1.payload,
        )
        assert import1.success

        # Step 3: LangGraph → Universal Schema
        export2 = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="mcp-agent-1",
            encrypt=False,
        )
        assert export2.success

        # Step 4: Universal Schema → New MCP adapter
        new_mcp = MCPAdapter()
        import2 = engine.import_state(
            adapter=new_mcp,
            payload=export2.payload,
            agent_id="roundtrip-agent",
        )
        assert import2.success

        # Verify conversation preserved through full roundtrip
        final = new_mcp.export_state("roundtrip-agent")
        assert len(final.cognitive_state.conversation_history) == original_msgs
