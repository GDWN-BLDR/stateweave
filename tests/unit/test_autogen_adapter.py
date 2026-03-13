"""
Unit Tests: AutoGen Adapter
==============================
AutoGen ↔ Universal Schema mapping tests.
"""

import pytest

from stateweave.adapters.autogen_adapter import AutoGenAdapter
from stateweave.adapters.base import ExportError
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestAutoGenAdapter:
    @pytest.fixture
    def adapter(self):
        return AutoGenAdapter()

    @pytest.fixture
    def adapter_with_agent(self):
        adapter = AutoGenAdapter()
        adapter.register_agent(
            "research-agent",
            {
                "name": "research_assistant",
                "system_message": "You are a helpful research assistant.",
                "description": "An agent that helps with research tasks",
                "human_input_mode": "NEVER",
                "chat_messages": {
                    "user_proxy": [
                        {"role": "user", "content": "Find papers on AI safety"},
                        {"role": "assistant", "content": "I'll search for that."},
                        {"role": "user", "content": "Focus on 2026 papers"},
                        {"role": "assistant", "content": "Here are 3 papers from 2026..."},
                    ],
                    "coder": [
                        {
                            "role": "user",
                            "content": "Can you implement the algorithm from paper 1?",
                        },
                        {"role": "assistant", "content": "Sure, here's the implementation..."},
                    ],
                },
                "function_results": {
                    "search_papers": {"count": 3, "papers": ["paper1", "paper2", "paper3"]},
                },
            },
        )
        return adapter

    @pytest.fixture
    def adapter_with_group_chat(self):
        adapter = AutoGenAdapter()
        adapter.register_agent(
            "group-agent",
            {
                "name": "group_manager",
                "system_message": "You manage the group discussion.",
                "chat_messages": {
                    "researcher": [
                        {"role": "user", "content": "What did you find?"},
                        {"role": "assistant", "content": "Here are the results."},
                    ],
                },
                "group_chat": {
                    "agents": ["researcher", "coder", "reviewer"],
                    "speaker_selection_method": "round_robin",
                    "max_round": 10,
                },
                "code_execution_config": {
                    "work_dir": "/tmp/autogen",
                    "use_docker": False,
                },
            },
        )
        return adapter

    def test_framework_name(self, adapter):
        assert adapter.framework_name == "autogen"

    def test_register_agent(self, adapter):
        adapter.register_agent("test", {"name": "test_agent", "chat_messages": {}})
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "test"

    def test_export_unregistered_fails(self, adapter):
        with pytest.raises(ExportError, match="not registered"):
            adapter.export_state("nonexistent")

    def test_export_registered_agent(self, adapter_with_agent):
        payload = adapter_with_agent.export_state("research-agent")
        assert payload.source_framework == "autogen"
        assert payload.metadata.agent_id == "research-agent"

    def test_system_message_in_working_memory(self, adapter_with_agent):
        payload = adapter_with_agent.export_state("research-agent")
        wm = payload.cognitive_state.working_memory
        assert wm["system_message"] == "You are a helpful research assistant."
        assert wm["agent_description"] == "An agent that helps with research tasks"
        assert wm["agent_name"] == "research_assistant"

    def test_multi_counterpart_messages(self, adapter_with_agent):
        payload = adapter_with_agent.export_state("research-agent")
        msgs = payload.cognitive_state.conversation_history
        # 4 from user_proxy + 2 from coder = 6
        assert len(msgs) == 6

    def test_counterpart_preserved_in_metadata(self, adapter_with_agent):
        payload = adapter_with_agent.export_state("research-agent")
        msgs = payload.cognitive_state.conversation_history
        counterparts = {m.metadata.get("counterpart") for m in msgs if m.metadata}
        assert "user_proxy" in counterparts
        assert "coder" in counterparts

    def test_function_results_exported(self, adapter_with_agent):
        payload = adapter_with_agent.export_state("research-agent")
        tc = payload.cognitive_state.tool_results_cache
        assert "search_papers" in tc

    def test_group_chat_warning(self, adapter_with_group_chat):
        payload = adapter_with_group_chat.export_state("group-agent")
        gc_warnings = [w for w in payload.non_portable_warnings if "group_chat" in w.field]
        assert len(gc_warnings) >= 1

    def test_code_execution_warning(self, adapter_with_group_chat):
        payload = adapter_with_group_chat.export_state("group-agent")
        ce_warnings = [w for w in payload.non_portable_warnings if "code_execution" in w.field]
        assert len(ce_warnings) >= 1

    def test_import_state(self, adapter):
        payload = StateWeavePayload(
            source_framework="mcp",
            metadata=AgentMetadata(agent_id="mcp-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello", name="user_proxy"),
                    Message(role=MessageRole.ASSISTANT, content="Hi!", name="user_proxy"),
                ],
                working_memory={
                    "system_message": "You are helpful.",
                    "agent_name": "imported_agent",
                },
            ),
        )
        result = adapter.import_state(payload, agent_id="imported")
        assert result["framework"] == "autogen"
        assert result["import_source"] == "mcp"
        assert result["message_count"] == 2

    def test_roundtrip_export_import(self, adapter_with_agent):
        exported = adapter_with_agent.export_state("research-agent")

        target = AutoGenAdapter()
        result = target.import_state(exported, agent_id="roundtrip")

        re_exported = target.export_state("roundtrip")
        assert len(re_exported.cognitive_state.conversation_history) == 6
        wm = re_exported.cognitive_state.working_memory
        assert wm["system_message"] == "You are a helpful research assistant."

    def test_state_corruption_detection(self, adapter):
        adapter.register_agent(
            "corrupted",
            {
                "name": "broken_agent",
                "chat_messages": {
                    "user": "not a list",  # Corruption: should be a list
                },
            },
        )
        payload = adapter.export_state("corrupted")
        critical = [w for w in payload.non_portable_warnings if w.severity.value == "CRITICAL"]
        assert len(critical) >= 1

    def test_none_content_warning(self, adapter):
        adapter.register_agent(
            "none-content",
            {
                "name": "edge_case_agent",
                "chat_messages": {
                    "user": [
                        {"role": "assistant", "content": None},  # Corruption indicator
                    ],
                },
            },
        )
        payload = adapter.export_state("none-content")
        none_warnings = [w for w in payload.non_portable_warnings if "None content" in w.reason]
        assert len(none_warnings) >= 1

    def test_list_agents(self, adapter_with_agent):
        agents = adapter_with_agent.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "autogen"
        assert agents[0].agent_name == "research_assistant"
