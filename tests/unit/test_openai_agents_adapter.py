"""Tests for OpenAI Agents SDK adapter."""

from stateweave.adapters.openai_agents_adapter import OpenAIAgentsAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestOpenAIAgentsAdapter:
    """Test suite for OpenAIAgentsAdapter."""

    def test_framework_name(self):
        adapter = OpenAIAgentsAdapter()
        assert adapter.framework_name == "openai_agents"

    def test_export_state_empty(self):
        adapter = OpenAIAgentsAdapter()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "openai_agents"
        assert payload.metadata.agent_id == "test-agent"

    def test_import_state_basic(self):
        adapter = OpenAIAgentsAdapter()
        payload = StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="imported"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                ],
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "openai_agents"

    def test_round_trip_with_messages(self):
        adapter = OpenAIAgentsAdapter()
        adapter._agents["test"] = {
            "session_messages": [
                {"role": "user", "content": "What is OpenAI?"},
                {"role": "assistant", "content": "An AI company."},
            ],
            "instructions": "You are a helpful assistant.",
            "model": "gpt-4",
        }

        original = adapter._extract_state
        adapter._extract_state = lambda agent_id="", include_tools=True: adapter._agents["test"]

        payload = adapter.export_state("test")
        assert len(payload.cognitive_state.conversation_history) == 2
        assert payload.cognitive_state.working_memory.get("openai_instructions") is not None
        assert payload.cognitive_state.working_memory.get("openai_model") == "gpt-4"

    def test_handoffs_to_goal_tree(self):
        adapter = OpenAIAgentsAdapter()
        state = {
            "handoffs": [
                {"target_agent": "triage", "name": "triage_handoff"},
                {"target_agent": "specialist", "name": "specialist_handoff"},
            ]
        }
        cs = adapter._translate_to_cognitive_state(state)
        assert len(cs.goal_tree) == 2
        assert "handoff_0" in cs.goal_tree
        assert "triage" in cs.goal_tree["handoff_0"].description

    def test_non_portable_session_warning(self):
        class FakeSession:
            pass

        adapter = OpenAIAgentsAdapter(session=FakeSession())
        state = {}
        warnings = adapter._detect_non_portable(state)
        session_warns = [w for w in warnings if w.field == "session"]
        assert len(session_warns) == 1

    def test_non_portable_handoffs_warning(self):
        adapter = OpenAIAgentsAdapter()
        state = {"handoffs": [{"target_agent": "other"}]}
        warnings = adapter._detect_non_portable(state)
        handoff_warns = [w for w in warnings if w.field == "handoffs"]
        assert len(handoff_warns) == 1

    def test_list_agents_empty(self):
        adapter = OpenAIAgentsAdapter()
        assert adapter.list_agents() == []

    def test_validate_payload(self):
        adapter = OpenAIAgentsAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
