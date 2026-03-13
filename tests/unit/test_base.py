"""
Unit Tests: Adapter Base
===========================
Tests for the StateWeaveAdapter ABC.
"""

import pytest

from stateweave.adapters.base import StateWeaveAdapter
from stateweave.schema.v1 import AgentMetadata, StateWeavePayload


class TestAdapterBase:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            StateWeaveAdapter()

    def test_validate_payload(self):
        from stateweave.adapters.langgraph_adapter import LangGraphAdapter

        adapter = LangGraphAdapter()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid"),
        )
        assert adapter.validate_payload(payload) is True
