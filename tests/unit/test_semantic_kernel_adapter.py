"""Tests for Semantic Kernel adapter."""

from stateweave.adapters.semantic_kernel_adapter import SemanticKernelAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestSemanticKernelAdapter:
    """Test suite for SemanticKernelAdapter."""

    def test_framework_name(self):
        adapter = SemanticKernelAdapter()
        assert adapter.framework_name == "semantic_kernel"

    def test_export_state_empty(self):
        adapter = SemanticKernelAdapter()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "semantic_kernel"
        assert "microsoft" in payload.metadata.tags

    def test_import_state_basic(self):
        adapter = SemanticKernelAdapter()
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
        assert result["framework"] == "semantic_kernel"

    def test_round_trip(self):
        adapter = SemanticKernelAdapter()
        payload = adapter.export_state("rt-test")
        result = adapter.import_state(payload)
        assert result["agent_id"] == "rt-test"

    def test_list_agents_empty(self):
        adapter = SemanticKernelAdapter()
        assert adapter.list_agents() == []

    def test_list_agents_after_import(self):
        adapter = SemanticKernelAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="imported"),
        )
        adapter.import_state(payload)
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "semantic_kernel"

    def test_validate_payload(self):
        adapter = SemanticKernelAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
