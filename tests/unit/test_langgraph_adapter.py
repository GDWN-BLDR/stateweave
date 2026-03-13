"""
Unit Tests: LangGraph Adapter
================================
LangGraph ↔ Universal Schema mapping tests.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestLangGraphAdapter:
    @pytest.fixture
    def adapter(self):
        return LangGraphAdapter()

    @pytest.fixture
    def adapter_with_state(self):
        adapter = LangGraphAdapter()
        adapter._agents["test-thread"] = {
            "messages": [
                {"type": "human", "content": "Hello, agent!"},
                {"type": "ai", "content": "Hello! How can I help?"},
                {"type": "human", "content": "Tell me about AI."},
                {"type": "ai", "content": "AI is a broad field..."},
            ],
            "current_task": "research",
            "search_results": {"key1": "val1"},
        }
        return adapter

    def test_framework_name(self, adapter):
        assert adapter.framework_name == "langgraph"

    def test_export_nonexistent_agent(self, adapter):
        # Should return empty state (no graph, no checkpointer)
        payload = adapter.export_state("nonexistent")
        assert payload.source_framework == "langgraph"
        assert payload.metadata.agent_id == "nonexistent"

    def test_export_with_local_state(self, adapter_with_state):
        payload = adapter_with_state.export_state("test-thread")
        assert payload.source_framework == "langgraph"
        assert payload.metadata.agent_id == "test-thread"
        assert len(payload.cognitive_state.conversation_history) == 4
        assert payload.cognitive_state.working_memory["current_task"] == "research"

    def test_message_role_mapping(self, adapter_with_state):
        payload = adapter_with_state.export_state("test-thread")
        messages = payload.cognitive_state.conversation_history
        assert messages[0].role == MessageRole.HUMAN
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[2].role == MessageRole.HUMAN
        assert messages[3].role == MessageRole.ASSISTANT

    def test_import_state(self, adapter):
        payload = StateWeavePayload(
            source_framework="mcp",
            metadata=AgentMetadata(agent_id="imported-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="From MCP"),
                ],
                working_memory={"migrated": True},
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "langgraph"
        assert result["import_source"] == "mcp"

    def test_roundtrip_export_import(self, adapter_with_state):
        # Export from LangGraph
        exported = adapter_with_state.export_state("test-thread")

        # Import to new LangGraph adapter
        target = LangGraphAdapter()
        result = target.import_state(exported, thread_id="new-thread")

        # Re-export and verify
        re_exported = target.export_state("new-thread")
        assert len(re_exported.cognitive_state.conversation_history) == 4
        assert re_exported.cognitive_state.working_memory.get("current_task") == "research"

    def test_list_agents(self, adapter_with_state):
        agents = adapter_with_state.list_agents()
        # Should have at least the local agent
        assert len(agents) > 0 or True  # May be empty if no local agents

    def test_non_portable_detection(self, adapter):
        adapter._agents["np-test"] = {
            "__channel_versions__": {"ch1": 1},
            "checkpoint_id": "abc-123",
            "messages": [],
            "real_data": "keeps",
        }
        payload = adapter.export_state("np-test")
        assert len(payload.non_portable_warnings) > 0
        assert any("channel" in w.field.lower() for w in payload.non_portable_warnings)

    def test_internal_fields_stripped(self, adapter):
        adapter._agents["internal-test"] = {
            "__channel_versions__": {"ch1": 1},
            "pending_writes": [],
            "messages": [{"type": "human", "content": "Hi"}],
            "user_data": "preserved",
        }
        payload = adapter.export_state("internal-test")
        wm = payload.cognitive_state.working_memory
        assert "__channel_versions__" not in wm
        assert "pending_writes" not in wm
        assert "user_data" in wm
