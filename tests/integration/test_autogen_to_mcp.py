"""
Integration Tests: AutoGen ↔ MCP Migration
=============================================
Full migration pipeline between AutoGen and MCP.
"""

import pytest

from stateweave.adapters.autogen_adapter import AutoGenAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.migration import MigrationEngine


class TestAutoGenToMCPMigration:
    @pytest.fixture
    def autogen_adapter(self):
        adapter = AutoGenAdapter()
        adapter.register_agent(
            "ag-1",
            {
                "name": "coder",
                "system_message": "You write Python code.",
                "chat_messages": {
                    "user_proxy": [
                        {"role": "user", "content": "Write a fibonacci function"},
                        {
                            "role": "assistant",
                            "content": "def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)",
                        },
                    ],
                },
                "function_results": {
                    "execute_code": {"success": True, "output": "fib(10) = 55"},
                },
            },
        )
        return adapter

    @pytest.fixture
    def mcp_adapter(self):
        return MCPAdapter()

    @pytest.fixture
    def engine(self):
        return MigrationEngine()

    def test_autogen_to_mcp(self, autogen_adapter, mcp_adapter, engine):
        export = engine.export_state(autogen_adapter, "ag-1", encrypt=False)
        assert export.success
        assert export.payload.source_framework == "autogen"

        result = engine.import_state(mcp_adapter, payload=export.payload)
        assert result.success

    def test_conversation_preserved(self, autogen_adapter, mcp_adapter, engine):
        export = engine.export_state(autogen_adapter, "ag-1", encrypt=False)
        msgs = export.payload.cognitive_state.conversation_history
        assert len(msgs) == 2

        engine.import_state(mcp_adapter, payload=export.payload)
        re_exported = mcp_adapter.export_state("ag-1")
        assert len(re_exported.cognitive_state.conversation_history) == 2

    def test_mcp_to_autogen(self, mcp_adapter, engine):
        mcp_adapter.register_agent(
            "mcp-1",
            {
                "messages": [
                    {"role": "user", "content": "Search for Python tutorials"},
                    {"role": "assistant", "content": "Found 10 results."},
                ],
                "tool_calls": [
                    {
                        "name": "search",
                        "arguments": {"q": "python tutorials"},
                        "result": {"count": 10},
                        "success": True,
                    },
                ],
            },
        )
        export = engine.export_state(mcp_adapter, "mcp-1", encrypt=False)

        autogen = AutoGenAdapter()
        result = engine.import_state(autogen, payload=export.payload, agent_id="migrated")
        assert result.success

        re_exported = autogen.export_state("migrated")
        assert len(re_exported.cognitive_state.conversation_history) == 2

    def test_four_way_migration(self, engine):
        """AutoGen → MCP → LangGraph → CrewAI roundtrip."""
        from stateweave.adapters.crewai_adapter import CrewAIAdapter
        from stateweave.adapters.langgraph_adapter import LangGraphAdapter

        # Start in AutoGen
        ag = AutoGenAdapter()
        ag.register_agent(
            "origin",
            {
                "name": "traveler",
                "system_message": "You are a traveling agent.",
                "chat_messages": {
                    "user": [
                        {"role": "user", "content": "Hello from AutoGen"},
                        {"role": "assistant", "content": "Hello! I'm traveling the frameworks."},
                    ],
                },
            },
        )

        # AutoGen → MCP
        e1 = engine.export_state(ag, "origin", encrypt=False)
        mcp = MCPAdapter()
        engine.import_state(mcp, payload=e1.payload)

        # MCP → LangGraph
        e2 = engine.export_state(mcp, "origin", encrypt=False)
        lg = LangGraphAdapter()
        engine.import_state(lg, payload=e2.payload)

        # LangGraph → CrewAI
        e3 = engine.export_state(lg, "origin", encrypt=False)
        crew = CrewAIAdapter()
        engine.import_state(crew, payload=e3.payload, crew_id="final")

        # Verify conversation survived 4 hops
        final = crew.export_state("final")
        assert len(final.cognitive_state.conversation_history) == 2
        assert any(
            "Hello from AutoGen" in m.content for m in final.cognitive_state.conversation_history
        )
