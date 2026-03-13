"""Tests for Haystack adapter."""

from stateweave.adapters.haystack_adapter import HaystackAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestHaystackAdapter:
    """Test suite for HaystackAdapter."""

    def test_framework_name(self):
        adapter = HaystackAdapter()
        assert adapter.framework_name == "haystack"

    def test_export_state_empty(self):
        adapter = HaystackAdapter()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "haystack"
        assert payload.metadata.agent_id == "test-agent"

    def test_import_state_basic(self):
        adapter = HaystackAdapter()
        payload = StateWeavePayload(
            source_framework="dspy",
            metadata=AgentMetadata(agent_id="imported"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                ],
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "haystack"

    def test_round_trip(self):
        adapter = HaystackAdapter()
        payload = adapter.export_state("rt-test")
        result = adapter.import_state(payload)
        assert result["agent_id"] == "rt-test"

    def test_list_agents_empty(self):
        adapter = HaystackAdapter()
        assert adapter.list_agents() == []

    def test_list_agents_after_import(self):
        adapter = HaystackAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="imported"),
        )
        adapter.import_state(payload)
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "haystack"

    def test_validate_payload(self):
        adapter = HaystackAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
