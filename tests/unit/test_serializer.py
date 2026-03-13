"""
Unit Tests: StateWeave Serializer
===================================
Round-trip serialization tests, typed serialization, error handling.
"""

import pytest

from stateweave.core.serializer import SerializationError, StateWeaveSerializer
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestStateWeaveSerializer:
    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @pytest.fixture
    def pretty_serializer(self):
        return StateWeaveSerializer(pretty=True)

    @pytest.fixture
    def sample_payload(self):
        return StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="test-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                    Message(role=MessageRole.ASSISTANT, content="Hi there!"),
                ],
                working_memory={"task": "testing", "count": 42},
            ),
        )

    def test_dumps_returns_bytes(self, serializer, sample_payload):
        result = serializer.dumps(sample_payload)
        assert isinstance(result, bytes)

    def test_loads_returns_payload(self, serializer, sample_payload):
        raw = serializer.dumps(sample_payload)
        restored = serializer.loads(raw)
        assert isinstance(restored, StateWeavePayload)

    def test_roundtrip(self, serializer, sample_payload):
        raw = serializer.dumps(sample_payload)
        restored = serializer.loads(raw)
        assert restored.source_framework == "langgraph"
        assert restored.metadata.agent_id == "test-agent"
        assert len(restored.cognitive_state.conversation_history) == 2
        assert restored.cognitive_state.working_memory["task"] == "testing"
        assert restored.cognitive_state.working_memory["count"] == 42

    def test_pretty_output(self, pretty_serializer, sample_payload):
        raw = pretty_serializer.dumps(sample_payload)
        text = raw.decode("utf-8")
        assert "\n" in text  # Pretty-printed JSON has newlines

    def test_dumps_typed(self, serializer, sample_payload):
        type_str, data = serializer.dumps_typed(sample_payload)
        assert type_str.startswith("stateweave.v1.")
        assert "langgraph" in type_str
        assert isinstance(data, bytes)

    def test_loads_typed_roundtrip(self, serializer, sample_payload):
        typed = serializer.dumps_typed(sample_payload)
        restored = serializer.loads_typed(typed)
        assert restored.source_framework == "langgraph"

    def test_loads_typed_wrong_prefix(self, serializer):
        with pytest.raises(SerializationError, match="Unknown type string"):
            serializer.loads_typed(("wrong.prefix", b"{}"))

    def test_loads_invalid_json(self, serializer):
        with pytest.raises(SerializationError, match="Invalid JSON"):
            serializer.loads(b"not valid json")

    def test_to_dict(self, serializer, sample_payload):
        d = serializer.to_dict(sample_payload)
        assert isinstance(d, dict)
        assert d["source_framework"] == "langgraph"

    def test_from_dict(self, serializer):
        d = {
            "source_framework": "mcp",
            "metadata": {"agent_id": "dict-agent"},
        }
        payload = serializer.from_dict(d)
        assert payload.source_framework == "mcp"

    def test_from_dict_invalid(self, serializer):
        with pytest.raises(SerializationError):
            serializer.from_dict({"invalid": True})

    def test_encode_decode_binary(self):
        original = b"\x00\x01\x02\xff\xfe"
        encoded = StateWeaveSerializer.encode_binary(original)
        decoded = StateWeaveSerializer.decode_binary(encoded)
        assert decoded == original

    def test_empty_payload_roundtrip(self, serializer):
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="empty"),
        )
        raw = serializer.dumps(payload)
        restored = serializer.loads(raw)
        assert restored.cognitive_state.conversation_history == []
        assert restored.cognitive_state.working_memory == {}
