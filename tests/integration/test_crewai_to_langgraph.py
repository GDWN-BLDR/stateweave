"""
Integration Tests: CrewAI ↔ LangGraph Migration
==================================================
Full migration pipeline between CrewAI and LangGraph.
"""

import pytest

from stateweave.adapters.crewai_adapter import CrewAIAdapter
from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.core.migration import MigrationEngine


class TestCrewAIToLangGraphMigration:
    @pytest.fixture
    def crewai_adapter(self):
        adapter = CrewAIAdapter()
        adapter.register_crew(
            "crew-1",
            {
                "process_type": "sequential",
                "agents": [
                    {
                        "role": "Analyst",
                        "goal": "Analyze data",
                        "backstory": "Data expert",
                        "tools": ["sql_query"],
                    },
                ],
                "tasks": [
                    {
                        "description": "Analyze sales data",
                        "expected_output": "Report",
                        "output": "Sales up 15%",
                    },
                ],
                "execution_log": [
                    {
                        "role": "agent",
                        "agent_role": "Analyst",
                        "content": "Analyzing sales data...",
                    },
                    {
                        "role": "tool",
                        "agent_role": "Analyst",
                        "content": "Query returned 1000 rows",
                    },
                    {
                        "role": "agent",
                        "agent_role": "Analyst",
                        "content": "Sales are up 15% this quarter.",
                    },
                ],
            },
        )
        return adapter

    @pytest.fixture
    def langgraph_adapter(self):
        return LangGraphAdapter()

    @pytest.fixture
    def engine(self):
        return MigrationEngine()

    def test_crewai_to_langgraph(self, crewai_adapter, langgraph_adapter, engine):
        export = engine.export_state(crewai_adapter, "crew-1", encrypt=False)
        assert export.success
        assert export.payload.source_framework == "crewai"

        result = engine.import_state(langgraph_adapter, payload=export.payload)
        assert result.success

    def test_conversation_preserved(self, crewai_adapter, langgraph_adapter, engine):
        export = engine.export_state(crewai_adapter, "crew-1", encrypt=False)
        msgs = export.payload.cognitive_state.conversation_history
        assert len(msgs) == 3

        engine.import_state(langgraph_adapter, payload=export.payload)
        re_exported = langgraph_adapter.export_state("crew-1")
        assert len(re_exported.cognitive_state.conversation_history) == 3

    def test_langgraph_to_crewai(self, langgraph_adapter, engine):
        langgraph_adapter._agents["lg-1"] = {
            "messages": [
                {"type": "human", "content": "Analyze this data"},
                {"type": "ai", "content": "I'll analyze it now."},
            ],
            "task": "analysis",
        }
        export = engine.export_state(langgraph_adapter, "lg-1", encrypt=False)

        crewai = CrewAIAdapter()
        result = engine.import_state(crewai, payload=export.payload, crew_id="migrated")
        assert result.success

        re_exported = crewai.export_state("migrated")
        assert len(re_exported.cognitive_state.conversation_history) == 2

    def test_bidirectional_roundtrip(self, crewai_adapter, engine):
        # CrewAI → LangGraph → CrewAI
        export1 = engine.export_state(crewai_adapter, "crew-1", encrypt=False)
        original_count = len(export1.payload.cognitive_state.conversation_history)

        lg = LangGraphAdapter()
        engine.import_state(lg, payload=export1.payload)

        export2 = engine.export_state(lg, "crew-1", encrypt=False)

        crewai2 = CrewAIAdapter()
        engine.import_state(crewai2, payload=export2.payload, crew_id="roundtrip")

        final = crewai2.export_state("roundtrip")
        assert len(final.cognitive_state.conversation_history) == original_count
