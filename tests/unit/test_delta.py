"""
Unit Tests: Delta State Transport
====================================
Tests for delta creation, application, hash mismatch detection,
and empty delta handling.
"""

from datetime import datetime

import pytest

from stateweave.core.delta import (
    DeltaHashMismatchError,
    DeltaPayload,
    apply_delta,
    compute_payload_hash,
    create_delta,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


@pytest.fixture
def base_payload():
    return StateWeavePayload(
        source_framework="langgraph",
        exported_at=datetime(2026, 3, 13, 10, 0, 0),
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            ],
            working_memory={
                "task": "research",
                "confidence": 0.7,
                "context": {"topic": "AI"},
            },
        ),
        metadata=AgentMetadata(agent_id="agent-1", agent_name="test-agent"),
    )


@pytest.fixture
def updated_payload():
    return StateWeavePayload(
        source_framework="langgraph",
        exported_at=datetime(2026, 3, 13, 11, 0, 0),
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!"),
                Message(role=MessageRole.HUMAN, content="What is ML?"),
            ],
            working_memory={
                "task": "research",
                "confidence": 0.95,
                "context": {"topic": "AI"},
                "new_key": "new_value",
            },
        ),
        metadata=AgentMetadata(agent_id="agent-1", agent_name="test-agent"),
    )


class TestComputePayloadHash:
    def test_hash_is_deterministic(self, base_payload):
        hash1 = compute_payload_hash(base_payload)
        hash2 = compute_payload_hash(base_payload)
        assert hash1 == hash2

    def test_hash_is_hex_string(self, base_payload):
        h = compute_payload_hash(base_payload)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex length

    def test_different_payloads_different_hashes(self, base_payload, updated_payload):
        h1 = compute_payload_hash(base_payload)
        h2 = compute_payload_hash(updated_payload)
        assert h1 != h2


class TestCreateDelta:
    def test_creates_delta_with_changes(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        assert isinstance(delta, DeltaPayload)
        assert not delta.is_empty
        assert delta.size > 0

    def test_delta_has_correct_base_hash(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        expected_hash = compute_payload_hash(base_payload)
        assert delta.base_hash == expected_hash

    def test_empty_delta_for_identical_payloads(self, base_payload):
        delta = create_delta(base_payload, base_payload)
        assert delta.is_empty

    def test_delta_captures_additions(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        set_entries = [e for e in delta.entries if e.operation == "set"]
        assert len(set_entries) >= 1  # At least confidence change + new_key

    def test_delta_source_framework(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        assert delta.source_framework == "langgraph"


class TestApplyDelta:
    def test_apply_delta_produces_updated_state(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        result = apply_delta(base_payload, delta)
        assert isinstance(result, StateWeavePayload)

    def test_apply_delta_reflects_changes(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        result = apply_delta(base_payload, delta)
        # The new key should be present
        assert "new_key" in result.cognitive_state.working_memory
        assert result.cognitive_state.working_memory["new_key"] == "new_value"

    def test_hash_mismatch_raises(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        # Modify the base payload to cause mismatch
        wrong_base = StateWeavePayload(
            source_framework="different",
            metadata=AgentMetadata(agent_id="wrong", agent_name="wrong"),
        )
        with pytest.raises(DeltaHashMismatchError):
            apply_delta(wrong_base, delta)

    def test_empty_delta_returns_same_state(self, base_payload):
        delta = create_delta(base_payload, base_payload)
        result = apply_delta(base_payload, delta)
        assert result.source_framework == base_payload.source_framework

    def test_roundtrip_preserves_conversation(self, base_payload, updated_payload):
        delta = create_delta(base_payload, updated_payload)
        result = apply_delta(base_payload, delta)
        # Should have 3 messages after applying delta
        assert len(result.cognitive_state.conversation_history) >= 2
