"""Tests for DSPy adapter."""

from stateweave.adapters.dspy_adapter import DSPyAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestDSPyAdapter:
    """Test suite for DSPyAdapter."""

    def test_framework_name(self):
        adapter = DSPyAdapter()
        assert adapter.framework_name == "dspy"

    def test_export_state_empty(self):
        adapter = DSPyAdapter()
        payload = adapter.export_state("test-module")
        assert payload.source_framework == "dspy"
        assert payload.metadata.agent_id == "test-module"
        assert len(payload.audit_trail) == 1
        assert payload.audit_trail[0].action.value == "export"

    def test_import_state_basic(self):
        adapter = DSPyAdapter()
        payload = StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="test-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="What is AI?"),
                ],
                working_memory={"dspy_signature": {"input": "question", "output": "answer"}},
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "dspy"
        assert result["import_source"] == "langgraph"

    def test_round_trip_with_demos(self):
        adapter = DSPyAdapter()

        # Simulate a state with demos
        adapter._agents["round-trip"] = {
            "demos": [
                {"question": "What is AI?", "answer": "Artificial Intelligence"},
                {"question": "What is ML?", "answer": "Machine Learning"},
            ],
            "signature": {"input_fields": ["question"], "output_fields": ["answer"]},
            "lm": {"model": "gpt-4", "temperature": 0.7},
        }

        # Override _get_module_state for testing
        original = adapter._get_module_state
        adapter._get_module_state = lambda agent_id="": adapter._agents["round-trip"]

        payload = adapter.export_state("round-trip")
        assert len(payload.cognitive_state.conversation_history) == 2
        assert payload.cognitive_state.working_memory.get("dspy_signature") is not None
        assert payload.cognitive_state.working_memory.get("dspy_lm_config") is not None

        # Import back
        result = adapter.import_state(payload, module_id="round-trip-2")
        assert result["framework"] == "dspy"
        assert "round-trip-2" in adapter._agents

    def test_list_agents_empty(self):
        adapter = DSPyAdapter()
        agents = adapter.list_agents()
        assert agents == []

    def test_list_agents_after_import(self):
        adapter = DSPyAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="imported"),
        )
        adapter.import_state(payload, module_id="my-module")
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "my-module"
        assert agents[0].framework == "dspy"

    def test_non_portable_warnings_api_key(self):
        adapter = DSPyAdapter()
        adapter._get_module_state = lambda agent_id="": {
            "lm": {"model": "gpt-4", "api_key": "sk-secret"},
        }
        payload = adapter.export_state("api-test")
        warnings = [w for w in payload.non_portable_warnings if w.field == "lm.api_key"]
        assert len(warnings) == 1
        assert warnings[0].severity.value == "CRITICAL"

    def test_non_portable_warnings_compiled(self):
        adapter = DSPyAdapter()
        adapter._get_module_state = lambda agent_id="": {"_compiled": True}
        payload = adapter.export_state("compiled-test")
        warnings = [w for w in payload.non_portable_warnings if w.field == "_compiled"]
        assert len(warnings) == 1
        assert warnings[0].data_loss is True

    def test_validate_payload(self):
        adapter = DSPyAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True

    def test_episodic_memory_from_train(self):
        adapter = DSPyAdapter()
        adapter._get_module_state = lambda agent_id="": {
            "train": [
                {"input": "What is AI?", "output": "Artificial Intelligence"},
            ]
        }
        payload = adapter.export_state("train-test")
        assert len(payload.cognitive_state.episodic_memory) == 1

    def test_traces_to_tool_results(self):
        adapter = DSPyAdapter()
        adapter._get_module_state = lambda agent_id="": {
            "traces": [
                {"inputs": {"q": "test"}, "outputs": {"a": "answer"}},
            ]
        }
        payload = adapter.export_state("trace-test")
        assert "trace_0" in payload.cognitive_state.tool_results_cache
