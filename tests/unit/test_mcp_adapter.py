"""
Unit Tests: MCP Adapter
========================
MCP ↔ Universal Schema mapping tests.
"""

import pytest

from stateweave.adapters.base import ExportError
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestMCPAdapter:
    @pytest.fixture
    def adapter(self):
        return MCPAdapter()

    @pytest.fixture
    def adapter_with_state(self):
        adapter = MCPAdapter()
        adapter.register_agent(
            "mcp-agent-1",
            {
                "messages": [
                    {"role": "user", "content": "Search for AI news"},
                    {"role": "assistant", "content": "Here are the results..."},
                ],
                "tool_calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "AI news"},
                        "result": {"urls": ["https://example.com"]},
                        "success": True,
                    },
                ],
                "resources": {
                    "weather://current": {"temp": "72F"},
                },
                "servers": ["mcp-server-filesystem", "mcp-server-weather"],
            },
        )
        return adapter

    def test_framework_name(self, adapter):
        assert adapter.framework_name == "mcp"

    def test_register_agent(self, adapter):
        adapter.register_agent("test", {"messages": []})
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "test"

    def test_export_unregistered_fails(self, adapter):
        with pytest.raises(ExportError, match="not registered"):
            adapter.export_state("nonexistent")

    def test_export_registered_agent(self, adapter_with_state):
        payload = adapter_with_state.export_state("mcp-agent-1")
        assert payload.source_framework == "mcp"
        assert payload.metadata.agent_id == "mcp-agent-1"
        assert len(payload.cognitive_state.conversation_history) == 2

    def test_message_role_mapping(self, adapter_with_state):
        payload = adapter_with_state.export_state("mcp-agent-1")
        messages = payload.cognitive_state.conversation_history
        assert messages[0].role == MessageRole.HUMAN
        assert messages[1].role == MessageRole.ASSISTANT

    def test_tool_calls_exported(self, adapter_with_state):
        payload = adapter_with_state.export_state("mcp-agent-1")
        assert "web_search" in payload.cognitive_state.tool_results_cache

    def test_resources_in_working_memory(self, adapter_with_state):
        payload = adapter_with_state.export_state("mcp-agent-1")
        wm = payload.cognitive_state.working_memory
        assert "resources" in wm

    def test_import_state(self, adapter):
        payload = StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="lg-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="From LangGraph"),
                ],
                working_memory={"task": "migrated"},
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "mcp"
        assert result["import_source"] == "langgraph"
        assert result["message_count"] == 1

    def test_roundtrip_export_import(self, adapter_with_state):
        exported = adapter_with_state.export_state("mcp-agent-1")

        target = MCPAdapter()
        result = target.import_state(exported, agent_id="migrated")

        re_exported = target.export_state("migrated")
        assert len(re_exported.cognitive_state.conversation_history) == 2

    def test_list_agents(self, adapter_with_state):
        agents = adapter_with_state.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "mcp"

    def test_non_portable_server_connections(self, adapter_with_state):
        payload = adapter_with_state.export_state("mcp-agent-1")
        server_warnings = [w for w in payload.non_portable_warnings if "server" in w.field.lower()]
        assert len(server_warnings) >= 1

    def test_oauth_token_detection(self, adapter):
        adapter.register_agent(
            "oauth-test",
            {
                "messages": [],
                "oauth_token": "bearer_secret",
            },
        )
        payload = adapter.export_state("oauth-test")
        critical = [w for w in payload.non_portable_warnings if w.severity.value == "CRITICAL"]
        assert len(critical) >= 1
