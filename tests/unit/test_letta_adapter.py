"""Tests for Letta/MemGPT adapter."""

from stateweave.adapters.letta_adapter import LettaAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestLettaAdapter:
    """Test suite for LettaAdapter."""

    def test_framework_name(self):
        adapter = LettaAdapter()
        assert adapter.framework_name == "letta"

    def test_export_state_empty(self):
        adapter = LettaAdapter()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "letta"
        assert "memgpt" in payload.metadata.tags

    def test_import_state_basic(self):
        adapter = LettaAdapter()
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
        assert result["framework"] == "letta"

    def test_core_memory_mapping(self):
        adapter = LettaAdapter(
            agent_state={
                "core_memory": {
                    "persona": "You are a friendly assistant.",
                    "human": "The user is Michael.",
                },
                "system": "You are MemGPT, a helpful AI.",
            }
        )
        payload = adapter.export_state("core-test")
        wm = payload.cognitive_state.working_memory
        assert wm.get("letta_core_persona") == "You are a friendly assistant."
        assert wm.get("letta_core_human") == "The user is Michael."
        assert wm.get("letta_system_prompt") == "You are MemGPT, a helpful AI."

    def test_archival_memory_mapping(self):
        adapter = LettaAdapter(
            agent_state={
                "archival_memory": [
                    {"text": "Fact 1: Python is a programming language."},
                    {"text": "Fact 2: LLMs are large language models."},
                ]
            }
        )
        payload = adapter.export_state("archival-test")
        assert "letta_archival" in payload.cognitive_state.long_term_memory
        assert len(payload.cognitive_state.episodic_memory) == 2

    def test_recall_memory_to_conversation(self):
        adapter = LettaAdapter(
            agent_state={
                "recall_memory": [
                    {"role": "user", "text": "What do you remember?"},
                    {"role": "assistant", "text": "I remember our past conversations."},
                ]
            }
        )
        payload = adapter.export_state("recall-test")
        assert len(payload.cognitive_state.conversation_history) == 2

    def test_non_portable_core_memory_warning(self):
        adapter = LettaAdapter(agent_state={"core_memory": {"persona": "test"}})
        payload = adapter.export_state("warn-test")
        core_warns = [w for w in payload.non_portable_warnings if w.field == "core_memory"]
        assert len(core_warns) == 1

    def test_non_portable_archival_warning(self):
        adapter = LettaAdapter(agent_state={"archival_memory": [{"text": "fact"}]})
        payload = adapter.export_state("arch-warn")
        arch_warns = [w for w in payload.non_portable_warnings if w.field == "archival_memory"]
        assert len(arch_warns) == 1
        assert arch_warns[0].data_loss is True

    def test_list_agents_empty(self):
        adapter = LettaAdapter()
        assert adapter.list_agents() == []

    def test_round_trip_core_memory(self):
        adapter = LettaAdapter(
            agent_state={
                "core_memory": {"persona": "I am helpful.", "human": "The user is Alice."},
                "system": "You are a chatbot.",
            }
        )
        payload = adapter.export_state("rt")
        result = adapter.import_state(payload, agent_id="rt-import")
        assert result["framework"] == "letta"
        imported = adapter._agents["rt-import"]
        assert imported.get("core_memory", {}).get("persona") == "I am helpful."
        assert imported.get("system") == "You are a chatbot."

    def test_validate_payload(self):
        adapter = LettaAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
