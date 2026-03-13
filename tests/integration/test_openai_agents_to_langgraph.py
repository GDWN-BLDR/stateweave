"""
Integration Tests: OpenAI Agents → LangGraph Migration
=========================================================
Full migration pipeline from OpenAI Agents SDK to LangGraph,
verifying session messages, handoffs, context, and instructions.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.openai_agents_adapter import OpenAIAgentsAdapter
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import MessageRole


class TestOpenAIAgentsToLangGraphMigration:
    @pytest.fixture
    def openai_adapter(self):
        adapter = OpenAIAgentsAdapter()
        adapter._agents["oai-agent-1"] = {
            "agent_name": "research-assistant",
            "instructions": "You are a helpful research assistant.",
            "model": "gpt-4o",
            "session_messages": [
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": "Find me papers on reinforcement learning."},
                {"role": "assistant", "content": "I'll search for recent papers on RL."},
                {
                    "role": "tool",
                    "content": "Found 15 papers on RL published in 2025-2026.",
                    "tool_call_id": "tc_search_1",
                },
                {"role": "assistant", "content": "I found 15 recent papers on RL."},
            ],
            "tools": [
                {"name": "search_papers", "description": "Search academic papers"},
                {"name": "summarize", "description": "Summarize a paper"},
            ],
            "handoffs": [
                {"target_agent": "writing-assistant", "name": "delegate_writing"},
            ],
            "context": {
                "user_id": "user_123",
                "session_topic": "reinforcement_learning",
                "max_results": 20,
            },
        }
        return adapter

    @pytest.fixture
    def langgraph_adapter(self):
        return LangGraphAdapter()

    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @pytest.fixture
    def encryption(self):
        return EncryptionFacade(EncryptionFacade.generate_key())

    def test_basic_migration(self, openai_adapter, langgraph_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )
        assert export_result.success
        assert export_result.payload.source_framework == "openai_agents"

        import_result = engine.import_state(
            adapter=langgraph_adapter,
            payload=export_result.payload,
        )
        assert import_result.success

        agents = langgraph_adapter.list_agents()
        assert any(a.agent_id == "oai-agent-1" for a in agents)

    def test_encrypted_migration(self, openai_adapter, langgraph_adapter, serializer, encryption):
        engine = MigrationEngine(serializer=serializer, encryption=encryption)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=True,
        )
        assert export_result.success
        assert export_result.encrypted_data is not None

        import_result = engine.import_state(
            adapter=langgraph_adapter,
            encrypted_data=export_result.encrypted_data,
            nonce=export_result.nonce,
        )
        assert import_result.success

    def test_messages_preserved(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        msgs = export_result.payload.cognitive_state.conversation_history
        assert len(msgs) == 5

        # Verify role mapping
        assert msgs[0].role == MessageRole.SYSTEM
        assert msgs[1].role == MessageRole.HUMAN
        assert msgs[2].role == MessageRole.ASSISTANT
        assert msgs[3].role == MessageRole.TOOL

    def test_instructions_preserved(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        wm = export_result.payload.cognitive_state.working_memory
        assert "openai_instructions" in wm
        assert "helpful research assistant" in wm["openai_instructions"]

    def test_context_preserved(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        wm = export_result.payload.cognitive_state.working_memory
        assert "openai_context" in wm
        assert wm["openai_context"]["session_topic"] == "reinforcement_learning"

    def test_handoffs_as_goal_tree(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        goal_tree = export_result.payload.cognitive_state.goal_tree
        assert len(goal_tree) >= 1
        handoff_goals = [g for g in goal_tree.values() if "Handoff" in g.description]
        assert len(handoff_goals) >= 1
        assert "writing-assistant" in handoff_goals[0].description

    def test_tools_as_tool_results(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        tool_results = export_result.payload.cognitive_state.tool_results_cache
        assert "search_papers" in tool_results
        assert "summarize" in tool_results

    def test_non_portable_warnings(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        warnings = export_result.payload.non_portable_warnings
        # Should warn about handoffs and tools
        assert len(warnings) >= 1

    def test_serialization_roundtrip(self, openai_adapter, serializer):
        engine = MigrationEngine(serializer=serializer)

        export_result = engine.export_state(
            adapter=openai_adapter,
            agent_id="oai-agent-1",
            encrypt=False,
        )

        raw = serializer.dumps(export_result.payload)
        restored = serializer.loads(raw)
        assert restored.source_framework == "openai_agents"
        assert len(restored.cognitive_state.conversation_history) == 5
