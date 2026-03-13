"""
Integration Tests: LangGraph → MCP Migration
===============================================
Full migration pipeline from LangGraph to MCP.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import (
    MessageRole,
)


class TestLangGraphToMCPMigration:
    @pytest.fixture
    def langgraph_adapter(self):
        adapter = LangGraphAdapter()
        adapter._agents["lg-thread-1"] = {
            "messages": [
                {"type": "human", "content": "What is the weather today?"},
                {"type": "ai", "content": "Let me check that for you."},
                {
                    "type": "tool",
                    "content": "72°F, sunny",
                    "name": "weather",
                    "tool_call_id": "tc_1",
                },
                {"type": "ai", "content": "The weather is 72°F and sunny!"},
            ],
            "current_task": "weather_check",
            "user_preferences": {"units": "fahrenheit"},
            "search_results": {"weather": {"temp": 72}},
        }
        return adapter

    @pytest.fixture
    def mcp_adapter(self):
        return MCPAdapter()

    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @pytest.fixture
    def encryption(self):
        return EncryptionFacade(EncryptionFacade.generate_key())

    def test_basic_migration(self, langgraph_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        # Export from LangGraph
        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=False,
        )
        assert export_result.success
        assert export_result.payload is not None

        # Import to MCP
        import_result = engine.import_state(
            adapter=mcp_adapter,
            payload=export_result.payload,
        )
        assert import_result.success

        # Verify MCP now has the agent
        agents = mcp_adapter.list_agents()
        assert any(a.agent_id == "lg-thread-1" for a in agents)

    def test_encrypted_migration(self, langgraph_adapter, mcp_adapter, serializer, encryption):
        engine = MigrationEngine(serializer=serializer, encryption=encryption)

        # Export with encryption
        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=True,
        )
        assert export_result.success
        assert export_result.encrypted_data is not None
        assert export_result.nonce is not None

        # Import with decryption
        import_result = engine.import_state(
            adapter=mcp_adapter,
            encrypted_data=export_result.encrypted_data,
            nonce=export_result.nonce,
        )
        assert import_result.success

    def test_conversation_preserved(self, langgraph_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=False,
        )

        # Verify conversation history preserved
        msgs = export_result.payload.cognitive_state.conversation_history
        assert len(msgs) == 4
        assert msgs[0].role == MessageRole.HUMAN
        assert msgs[0].content == "What is the weather today?"
        assert msgs[2].role == MessageRole.TOOL

        # Import and re-export from MCP
        engine.import_state(adapter=mcp_adapter, payload=export_result.payload)
        re_exported = mcp_adapter.export_state("lg-thread-1")
        assert len(re_exported.cognitive_state.conversation_history) == 4

    def test_working_memory_preserved(self, langgraph_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=False,
        )

        wm = export_result.payload.cognitive_state.working_memory
        assert wm["current_task"] == "weather_check"
        assert wm["user_preferences"] == {"units": "fahrenheit"}

    def test_serialization_roundtrip(self, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=False,
        )

        # Serialize and deserialize
        raw = serializer.dumps(export_result.payload)
        restored = serializer.loads(raw)
        assert restored.source_framework == "langgraph"
        assert len(restored.cognitive_state.conversation_history) == 4

    def test_audit_trail_populated(self, langgraph_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="lg-thread-1",
            encrypt=False,
        )
        assert len(export_result.audit_trail) >= 2  # export + validate

        import_result = engine.import_state(
            adapter=mcp_adapter,
            payload=export_result.payload,
        )
        assert len(import_result.audit_trail) >= 2  # validate + import
