"""
Property-Based Tests: Schema Roundtrip
=========================================
Hypothesis-based tests ensuring schema roundtrip invariants.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import (
    SCHEMA_VERSION,
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)

# Strategy for generating messages
message_strategy = st.builds(
    Message,
    role=st.sampled_from(list(MessageRole)),
    content=st.text(min_size=0, max_size=500),
    name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
)

# Strategy for generating working memory
working_memory_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30).filter(lambda x: x.isidentifier()),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none(),
    ),
    max_size=10,
)

# Strategy for generating cognitive states
cognitive_state_strategy = st.builds(
    CognitiveState,
    conversation_history=st.lists(message_strategy, max_size=20),
    working_memory=working_memory_strategy,
)

# Strategy for generating payloads
payload_strategy = st.builds(
    StateWeavePayload,
    source_framework=st.sampled_from(["langgraph", "mcp", "crewai", "autogen"]),
    metadata=st.builds(
        AgentMetadata,
        agent_id=st.text(min_size=1, max_size=50).filter(lambda x: len(x.strip()) > 0),
    ),
    cognitive_state=cognitive_state_strategy,
)


class TestSchemaRoundtrip:
    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @given(payload=payload_strategy)
    @settings(max_examples=50, deadline=5000)
    def test_serialization_roundtrip(self, payload):
        """Any valid payload should survive serialization roundtrip."""
        serializer = StateWeaveSerializer()
        raw = serializer.dumps(payload)
        restored = serializer.loads(raw)

        assert restored.stateweave_version == payload.stateweave_version
        assert restored.source_framework == payload.source_framework
        assert restored.metadata.agent_id == payload.metadata.agent_id
        assert len(restored.cognitive_state.conversation_history) == len(
            payload.cognitive_state.conversation_history
        )

    @given(payload=payload_strategy)
    @settings(max_examples=30, deadline=5000)
    def test_dict_roundtrip(self, payload):
        """Any valid payload should survive dict conversion roundtrip."""
        serializer = StateWeaveSerializer()
        d = serializer.to_dict(payload)
        restored = serializer.from_dict(d)

        assert restored.source_framework == payload.source_framework
        assert restored.metadata.agent_id == payload.metadata.agent_id

    @given(payload=payload_strategy)
    @settings(max_examples=30, deadline=5000)
    def test_typed_roundtrip(self, payload):
        """Any valid payload should survive typed serialization roundtrip."""
        serializer = StateWeaveSerializer()
        typed = serializer.dumps_typed(payload)
        restored = serializer.loads_typed(typed)

        assert restored.source_framework == payload.source_framework

    @given(payload=payload_strategy)
    @settings(max_examples=20, deadline=5000)
    def test_version_preserved(self, payload):
        """Schema version must never change during serialization."""
        serializer = StateWeaveSerializer()
        raw = serializer.dumps(payload)
        restored = serializer.loads(raw)
        assert restored.stateweave_version == SCHEMA_VERSION

    @given(
        messages=st.lists(message_strategy, min_size=1, max_size=50),
        wm=working_memory_strategy,
    )
    @settings(max_examples=30, deadline=5000)
    def test_cognitive_state_fidelity(self, messages, wm):
        """Cognitive state content must be preserved exactly."""
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="fidelity-test"),
            cognitive_state=CognitiveState(
                conversation_history=messages,
                working_memory=wm,
            ),
        )

        serializer = StateWeaveSerializer()
        raw = serializer.dumps(payload)
        restored = serializer.loads(raw)

        # Message count preserved
        assert len(restored.cognitive_state.conversation_history) == len(messages)

        # Working memory keys preserved
        assert set(restored.cognitive_state.working_memory.keys()) == set(wm.keys())

        # Message content preserved
        for orig, rest in zip(messages, restored.cognitive_state.conversation_history):
            assert rest.role == orig.role
            assert rest.content == orig.content
