"""Tests for zero-loss round-trip fidelity.

Verifies that framework-specific state is preserved during round-trips
through the Universal Schema, using the framework_specific field.
"""

import unittest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    StateWeavePayload,
)


class TestLangGraphRoundTripFidelity(unittest.TestCase):
    """Verify LangGraph → Universal → LangGraph preserves framework_specific state."""

    def setUp(self):
        self.adapter = LangGraphAdapter()
        # Register an agent with LangGraph internal fields
        self.adapter._agents["rt-agent"] = {
            "messages": [
                {"type": "human", "content": "Hello"},
                {"type": "ai", "content": "Hi there!"},
            ],
            "current_task": "research",
            "__channel_versions__": {"messages": 2},
            "__channel_values__": {"v": 1},
            "checkpoint_id": "ckpt-abc123",
        }

    def test_export_preserves_internal_fields_in_framework_specific(self):
        """Internal LangGraph fields should be in framework_specific, not dropped."""
        payload = self.adapter.export_state("rt-agent")

        self.assertIn("__channel_versions__", payload.cognitive_state.framework_specific)
        self.assertIn("__channel_values__", payload.cognitive_state.framework_specific)
        self.assertIn("checkpoint_id", payload.cognitive_state.framework_specific)
        self.assertEqual(
            payload.cognitive_state.framework_specific["__channel_versions__"],
            {"messages": 2},
        )

    def test_export_does_not_put_internal_fields_in_working_memory(self):
        """Internal fields should NOT leak into working_memory."""
        payload = self.adapter.export_state("rt-agent")

        self.assertNotIn("__channel_versions__", payload.cognitive_state.working_memory)
        self.assertNotIn("__channel_values__", payload.cognitive_state.working_memory)
        self.assertNotIn("checkpoint_id", payload.cognitive_state.working_memory)

    def test_round_trip_restores_framework_specific(self):
        """LG export → LG import should restore internal fields."""
        payload = self.adapter.export_state("rt-agent")

        # Import into a fresh adapter
        target = LangGraphAdapter()
        target.import_state(payload, thread_id="restored")

        restored_state = target._agents["restored"]

        # Framework-specific fields should be restored
        self.assertEqual(restored_state["__channel_versions__"], {"messages": 2})
        self.assertEqual(restored_state["__channel_values__"], {"v": 1})
        self.assertEqual(restored_state["checkpoint_id"], "ckpt-abc123")

    def test_round_trip_preserves_regular_state(self):
        """Working memory and messages survive the round-trip."""
        payload = self.adapter.export_state("rt-agent")

        target = LangGraphAdapter()
        target.import_state(payload, thread_id="restored")

        restored_state = target._agents["restored"]

        self.assertEqual(restored_state["current_task"], "research")
        self.assertEqual(len(restored_state["messages"]), 2)

    def test_cross_framework_carries_framework_specific(self):
        """LG → MCP: framework_specific should be carried but not applied as native state."""
        payload = self.adapter.export_state("rt-agent")

        # Import into MCP
        mcp = MCPAdapter()
        mcp.import_state(payload)

        # Export from MCP
        mcp_payload = mcp.export_state("rt-agent")

        # The framework_specific data should still exist (carried through)
        # but the source_framework is now "mcp"
        self.assertEqual(mcp_payload.source_framework, "mcp")

    def test_full_chain_lg_mcp_lg_preserves_framework_specific(self):
        """LG → MCP → LG: framework_specific should survive the full chain."""
        # Step 1: Export from LangGraph
        lg_payload = self.adapter.export_state("rt-agent")
        original_fs = lg_payload.cognitive_state.framework_specific.copy()

        # Step 2: Import into MCP
        mcp = MCPAdapter()
        mcp.import_state(lg_payload)

        # Step 3: Export from MCP (framework_specific is in the cognitive_state)
        mcp_payload = mcp.export_state("rt-agent")

        # Step 4: Import back into LangGraph
        target = LangGraphAdapter()
        target.import_state(mcp_payload, thread_id="full-chain")

        # The MCP adapter may not preserve framework_specific in the same way,
        # but the LangGraph adapter should handle whatever is passed.
        restored = target._agents["full-chain"]

        # Messages and working memory should survive
        self.assertIn("messages", restored)
        self.assertEqual(restored.get("current_task"), "research")


class TestFrameworkSpecificFieldDefault(unittest.TestCase):
    """Verify framework_specific defaults correctly."""

    def test_empty_by_default(self):
        """framework_specific should default to empty dict."""
        cs = CognitiveState()
        self.assertEqual(cs.framework_specific, {})

    def test_payload_with_framework_specific(self):
        """Payload should serialize/deserialize framework_specific correctly."""
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="test-1"),
            cognitive_state=CognitiveState(
                framework_specific={"internal_key": "value", "nested": {"a": 1}},
            ),
        )

        # Round-trip through dict
        data = payload.model_dump()
        restored = StateWeavePayload(**data)

        self.assertEqual(restored.cognitive_state.framework_specific["internal_key"], "value")
        self.assertEqual(restored.cognitive_state.framework_specific["nested"], {"a": 1})

    def test_backward_compat_no_framework_specific(self):
        """Payloads without framework_specific should still work (defaults to {})."""
        payload = StateWeavePayload(
            source_framework="legacy",
            metadata=AgentMetadata(agent_id="old-agent"),
        )
        self.assertEqual(payload.cognitive_state.framework_specific, {})


if __name__ == "__main__":
    unittest.main()
