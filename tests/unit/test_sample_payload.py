"""
Unit Tests: create_sample_payload across all 10 adapters
==========================================================
Verifies that every adapter can produce a valid sample payload
and that it works end-to-end with checkpoint/diff/rollback.
"""

import tempfile

import pytest

# Get all registered adapters from the CLI ADAPTERS dict
from stateweave.cli import ADAPTERS
from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import StateWeavePayload


class TestCreateSamplePayload:
    """Tests for create_sample_payload across all adapters."""

    @pytest.fixture(params=sorted(ADAPTERS.keys()))
    def adapter_name(self, request):
        return request.param

    def test_returns_valid_payload(self, adapter_name):
        """Every adapter should return a valid StateWeavePayload."""
        adapter = ADAPTERS[adapter_name]()
        payload = adapter.create_sample_payload("test-agent")

        assert isinstance(payload, StateWeavePayload)
        assert payload.metadata.agent_id == "test-agent"
        assert payload.source_framework == adapter_name
        assert len(payload.cognitive_state.conversation_history) > 0
        assert len(payload.cognitive_state.working_memory) > 0

    def test_num_messages_parameter(self, adapter_name):
        """num_messages should control conversation length."""
        adapter = ADAPTERS[adapter_name]()

        p3 = adapter.create_sample_payload("a", num_messages=3)
        p5 = adapter.create_sample_payload("a", num_messages=5)

        assert len(p3.cognitive_state.conversation_history) == 3
        assert len(p5.cognitive_state.conversation_history) == 5

    def test_checkpoint_diff_rollback_cycle(self, adapter_name):
        """Sample payload should work end-to-end with time travel."""
        adapter = ADAPTERS[adapter_name]()
        payload = adapter.create_sample_payload("cycle-agent", num_messages=2)

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = CheckpointStore(store_dir=tmp_dir)

            # Checkpoint v1
            cp1 = store.checkpoint(payload, agent_id="cycle-agent", label="v1")
            assert cp1.version == 1

            # Modify and checkpoint v2
            payload.cognitive_state.working_memory["new_key"] = "new_value"
            cp2 = store.checkpoint(payload, agent_id="cycle-agent", label="v2")
            assert cp2.version == 2

            # Diff
            diff = store.diff_versions("cycle-agent", 1, 2)
            assert diff.has_changes

            # Rollback
            restored = store.rollback("cycle-agent", version=1)
            assert "new_key" not in restored.cognitive_state.working_memory


class TestCreateSamplePayloadEdgeCases:
    """Edge case tests for create_sample_payload."""

    def test_zero_messages(self):
        adapter = ADAPTERS["langgraph"]()
        payload = adapter.create_sample_payload("a", num_messages=0)
        assert len(payload.cognitive_state.conversation_history) == 0

    def test_large_message_count(self):
        """When num_messages exceeds sample pool, returns all available."""
        adapter = ADAPTERS["langgraph"]()
        payload = adapter.create_sample_payload("a", num_messages=20)
        # create_sample_payload has a finite sample pool (5 messages)
        # so requesting more returns min(requested, pool_size)
        assert len(payload.cognitive_state.conversation_history) >= 3

    def test_different_agent_ids(self):
        adapter = ADAPTERS["mcp"]()
        p1 = adapter.create_sample_payload("agent-alpha")
        p2 = adapter.create_sample_payload("agent-beta")
        assert p1.metadata.agent_id == "agent-alpha"
        assert p2.metadata.agent_id == "agent-beta"
