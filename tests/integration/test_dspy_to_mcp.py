"""
Integration Tests: DSPy → MCP Migration
==========================================
Full migration pipeline from DSPy to MCP, verifying demos,
signatures, LM config, and traces survive translation.
"""

import pytest

from stateweave.adapters.dspy_adapter import DSPyAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer


class TestDSPyToMCPMigration:
    @pytest.fixture
    def dspy_adapter(self):
        adapter = DSPyAdapter()
        adapter._agents["dspy-module-1"] = {
            "signature": {
                "input_fields": ["question"],
                "output_fields": ["answer", "confidence"],
            },
            "demos": [
                {"question": "What is 2+2?", "answer": "4"},
                {"question": "Capital of France?", "answer": "Paris"},
                {"question": "Largest planet?", "answer": "Jupiter"},
            ],
            "lm": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500,
            },
            "traces": [
                {
                    "inputs": {"question": "What is AI?"},
                    "outputs": {"answer": "Artificial Intelligence", "confidence": "0.95"},
                },
            ],
            "train": [
                {"question": "Color of sky?", "answer": "Blue"},
            ],
            "_compiled": True,
            "metadata": {"optimizer": "BootstrapFewShot"},
        }
        return adapter

    @pytest.fixture
    def mcp_adapter(self):
        return MCPAdapter()

    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @pytest.fixture
    def encryption(self):
        return EncryptionFacade(EncryptionFacade.generate_key())

    def test_basic_migration(self, dspy_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )
        assert export_result.success
        assert export_result.payload is not None
        assert export_result.payload.source_framework == "dspy"

        import_result = engine.import_state(
            adapter=mcp_adapter,
            payload=export_result.payload,
        )
        assert import_result.success

        agents = mcp_adapter.list_agents()
        assert any(a.agent_id == "dspy-module-1" for a in agents)

    def test_encrypted_migration(self, dspy_adapter, mcp_adapter, serializer, encryption):
        engine = MigrationEngine(serializer=serializer, encryption=encryption)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=True,
        )
        assert export_result.success
        assert export_result.encrypted_data is not None

        import_result = engine.import_state(
            adapter=mcp_adapter,
            encrypted_data=export_result.encrypted_data,
            nonce=export_result.nonce,
        )
        assert import_result.success

    def test_demos_preserved(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        # Demos should be in conversation history
        msgs = export_result.payload.cognitive_state.conversation_history
        assert len(msgs) >= 3  # At least 3 demos
        demo_msgs = [m for m in msgs if m.metadata.get("source") == "dspy_demo"]
        assert len(demo_msgs) == 3

    def test_signature_preserved(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        wm = export_result.payload.cognitive_state.working_memory
        assert "dspy_signature" in wm
        assert wm["dspy_signature"]["input_fields"] == ["question"]

    def test_lm_config_preserved(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        wm = export_result.payload.cognitive_state.working_memory
        assert "dspy_lm_config" in wm
        assert wm["dspy_lm_config"]["model"] == "gpt-4"

    def test_traces_preserved(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        tool_results = export_result.payload.cognitive_state.tool_results_cache
        trace_results = {k: v for k, v in tool_results.items() if v.tool_name == "dspy_trace"}
        assert len(trace_results) >= 1

    def test_non_portable_warnings_populated(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        # _compiled flag should generate a warning
        warnings = export_result.payload.non_portable_warnings
        compiled_warnings = [w for w in warnings if "_compiled" in w.field]
        assert len(compiled_warnings) >= 1

    def test_serialization_roundtrip(self, dspy_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        raw = serializer.dumps(export_result.payload)
        restored = serializer.loads(raw)
        assert restored.source_framework == "dspy"
        assert "dspy_signature" in restored.cognitive_state.working_memory

    def test_mcp_re_export_preserves_data(self, dspy_adapter, mcp_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=dspy_adapter,
            agent_id="dspy-module-1",
            encrypt=False,
        )

        engine.import_state(adapter=mcp_adapter, payload=export_result.payload)
        re_exported = mcp_adapter.export_state("dspy-module-1")

        # Core state should survive the roundtrip
        assert len(re_exported.cognitive_state.conversation_history) >= 3
        assert re_exported.source_framework == "mcp"
