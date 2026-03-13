"""Tests for LlamaIndex adapter."""

from stateweave.adapters.llamaindex_adapter import LlamaIndexAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestLlamaIndexAdapter:
    """Test suite for LlamaIndexAdapter."""

    def test_framework_name(self):
        adapter = LlamaIndexAdapter()
        assert adapter.framework_name == "llamaindex"

    def test_export_state_empty(self):
        adapter = LlamaIndexAdapter()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "llamaindex"
        assert payload.metadata.agent_id == "test-agent"

    def test_import_state_basic(self):
        adapter = LlamaIndexAdapter()
        payload = StateWeavePayload(
            source_framework="dspy",
            metadata=AgentMetadata(agent_id="imported"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                    Message(role=MessageRole.ASSISTANT, content="Hi"),
                ],
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "llamaindex"
        assert result["import_source"] == "dspy"

    def test_round_trip_with_history(self):
        adapter = LlamaIndexAdapter()
        adapter._agents["rt-test"] = {
            "chat_history": [
                {"role": "user", "content": "What is LlamaIndex?"},
                {"role": "assistant", "content": "A data framework for LLMs."},
            ],
            "context": {"step": 1, "data": "test"},
        }

        original = adapter._extract_state
        adapter._extract_state = lambda: adapter._agents["rt-test"]

        payload = adapter.export_state("rt-test")
        assert len(payload.cognitive_state.conversation_history) == 2
        assert "llamaindex_context" in payload.cognitive_state.working_memory

        result = adapter.import_state(payload, agent_id="rt-test-2")
        assert result["framework"] == "llamaindex"

    def test_memory_blocks_translation(self):
        adapter = LlamaIndexAdapter()
        state = {
            "memory_blocks": {
                "facts_extracted": {"content": "User likes Python"},
                "vector_store": {"content": "embedded docs"},
                "static_info": {"content": "system config"},
            }
        }
        cs = adapter._translate_to_cognitive_state(state)
        assert "facts_facts_extracted" in cs.long_term_memory
        assert "vectors_vector_store" in cs.long_term_memory
        assert "block_static_info" in cs.working_memory

    def test_non_portable_vector_warning(self):
        adapter = LlamaIndexAdapter()
        state = {
            "memory_blocks": {
                "vector_store": {"content": "embedded docs"},
            }
        }
        warnings = adapter._detect_non_portable(state)
        vector_warns = [w for w in warnings if "vector" in w.field.lower()]
        assert len(vector_warns) == 1
        assert vector_warns[0].data_loss is True

    def test_non_portable_tools_warning(self):
        adapter = LlamaIndexAdapter()
        state = {"tools": [{"name": "search", "description": "Search tool"}]}
        warnings = adapter._detect_non_portable(state)
        tool_warns = [w for w in warnings if w.field == "tools"]
        assert len(tool_warns) == 1

    def test_list_agents_empty(self):
        adapter = LlamaIndexAdapter()
        assert adapter.list_agents() == []

    def test_list_agents_after_import(self):
        adapter = LlamaIndexAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="my-agent"),
        )
        adapter.import_state(payload)
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "llamaindex"

    def test_validate_payload(self):
        adapter = LlamaIndexAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
