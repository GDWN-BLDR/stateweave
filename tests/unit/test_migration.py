"""
Unit Tests: Migration Engine
===============================
Tests for the migration pipeline orchestration.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    StateWeavePayload,
)


class TestMigrationEngine:
    @pytest.fixture
    def engine(self):
        return MigrationEngine()

    @pytest.fixture
    def engine_with_encryption(self):
        key = EncryptionFacade.generate_key()
        return MigrationEngine(encryption=EncryptionFacade(key))

    @pytest.fixture
    def lg_adapter(self):
        adapter = LangGraphAdapter()
        adapter._agents["test-1"] = {
            "messages": [{"type": "human", "content": "Hi"}],
            "task": "testing",
        }
        return adapter

    def test_export_without_encryption(self, engine, lg_adapter):
        result = engine.export_state(lg_adapter, "test-1", encrypt=False)
        assert result.success
        assert result.payload is not None
        assert result.encrypted_data is None

    def test_export_with_encryption(self, engine_with_encryption, lg_adapter):
        result = engine_with_encryption.export_state(lg_adapter, "test-1", encrypt=True)
        assert result.success
        assert result.encrypted_data is not None
        assert result.nonce is not None

    def test_import_from_payload(self, engine):
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="import-test"),
        )
        adapter = MCPAdapter()
        adapter.register_agent("import-test", {"messages": []})
        result = engine.import_state(adapter, payload=payload)
        assert result.success

    def test_import_decrypt(self, engine_with_encryption, lg_adapter):
        export = engine_with_encryption.export_state(lg_adapter, "test-1", encrypt=True)
        mcp = MCPAdapter()
        result = engine_with_encryption.import_state(
            adapter=mcp,
            encrypted_data=export.encrypted_data,
            nonce=export.nonce,
        )
        assert result.success

    def test_diff_states(self, engine):
        a = StateWeavePayload(
            source_framework="lg",
            metadata=AgentMetadata(agent_id="a"),
            cognitive_state=CognitiveState(working_memory={"x": 1}),
        )
        b = StateWeavePayload(
            source_framework="lg",
            metadata=AgentMetadata(agent_id="b"),
            cognitive_state=CognitiveState(working_memory={"x": 2}),
        )
        diff = engine.diff_states(a, b)
        assert diff.has_changes
