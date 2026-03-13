"""
Unit Tests: CrewAI Adapter
============================
CrewAI ↔ Universal Schema mapping tests.
"""

import pytest

from stateweave.adapters.base import ExportError
from stateweave.adapters.crewai_adapter import CrewAIAdapter
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestCrewAIAdapter:
    @pytest.fixture
    def adapter(self):
        return CrewAIAdapter()

    @pytest.fixture
    def adapter_with_crew(self):
        adapter = CrewAIAdapter()
        adapter.register_crew(
            "research-crew",
            {
                "process_type": "sequential",
                "agents": [
                    {
                        "role": "Researcher",
                        "goal": "Find relevant information about AI trends",
                        "backstory": "Expert at finding information",
                        "tools": ["web_search", "arxiv_search"],
                        "allow_delegation": False,
                    },
                    {
                        "role": "Writer",
                        "goal": "Write compelling reports based on research",
                        "backstory": "Expert technical writer",
                        "tools": [],
                        "allow_delegation": True,
                    },
                ],
                "tasks": [
                    {
                        "description": "Research the latest AI agent frameworks",
                        "expected_output": "A list of top 5 frameworks with pros/cons",
                        "agent": "Researcher",
                        "output": "1. LangGraph: ...\n2. CrewAI: ...",
                    },
                    {
                        "description": "Write a summary report",
                        "expected_output": "A 500-word report",
                        "agent": "Writer",
                        "output": "AI agent frameworks have evolved...",
                    },
                ],
                "execution_log": [
                    {"role": "system", "content": "Starting crew execution"},
                    {
                        "role": "agent",
                        "agent_role": "Researcher",
                        "content": "Searching for AI frameworks...",
                    },
                    {"role": "tool", "content": "Found 5 results", "agent_role": "Researcher"},
                    {"role": "agent", "agent_role": "Writer", "content": "Writing the report..."},
                ],
                "context": {"topic": "AI frameworks", "deadline": "2026-03-15"},
                "memory": {"long_term": {"previous_topics": ["ML", "NLP"]}},
            },
        )
        return adapter

    def test_framework_name(self, adapter):
        assert adapter.framework_name == "crewai"

    def test_register_crew(self, adapter):
        adapter.register_crew("test", {"agents": [], "tasks": []})
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "test"

    def test_export_unregistered_fails(self, adapter):
        with pytest.raises(ExportError, match="not registered"):
            adapter.export_state("nonexistent")

    def test_export_registered_crew(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        assert payload.source_framework == "crewai"
        assert payload.metadata.agent_id == "research-crew"

    def test_agents_in_working_memory(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        wm = payload.cognitive_state.working_memory
        assert "agent_profiles" in wm
        assert "Researcher" in wm["agent_profiles"]
        assert "Writer" in wm["agent_profiles"]
        assert (
            wm["agent_profiles"]["Researcher"]["goal"]
            == "Find relevant information about AI trends"
        )

    def test_tasks_in_working_memory(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        wm = payload.cognitive_state.working_memory
        assert "task_0" in wm
        assert "task_1" in wm

    def test_task_results_in_tool_cache(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        tc = payload.cognitive_state.tool_results_cache
        assert "task_0" in tc
        assert tc["task_0"].tool_name == "crewai_task_0"

    def test_execution_log_to_messages(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        msgs = payload.cognitive_state.conversation_history
        assert len(msgs) == 4
        assert msgs[0].role == MessageRole.SYSTEM

    def test_goal_tree_from_agents(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        goals = payload.cognitive_state.goal_tree
        assert len(goals) >= 2

    def test_context_in_working_memory(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        wm = payload.cognitive_state.working_memory
        assert wm["crew_context"]["topic"] == "AI frameworks"
        assert "crew_memory" in wm

    def test_process_type_warning(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        pt_warnings = [w for w in payload.non_portable_warnings if "process_type" in w.field]
        assert len(pt_warnings) == 1
        assert "sequential" in pt_warnings[0].reason

    def test_delegation_warning(self, adapter_with_crew):
        payload = adapter_with_crew.export_state("research-crew")
        del_warnings = [w for w in payload.non_portable_warnings if "delegation" in w.field]
        assert len(del_warnings) >= 1

    def test_import_state(self, adapter):
        payload = StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="lg-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Research AI"),
                ],
                working_memory={"task": "research"},
            ),
        )
        result = adapter.import_state(payload, crew_id="imported")
        assert result["framework"] == "crewai"
        assert result["import_source"] == "langgraph"

    def test_roundtrip_export_import(self, adapter_with_crew):
        exported = adapter_with_crew.export_state("research-crew")

        target = CrewAIAdapter()
        result = target.import_state(exported, crew_id="roundtrip")

        re_exported = target.export_state("roundtrip")
        assert len(re_exported.cognitive_state.conversation_history) == 4
        assert "agent_profiles" in re_exported.cognitive_state.working_memory

    def test_list_agents(self, adapter_with_crew):
        agents = adapter_with_crew.list_agents()
        assert len(agents) == 1
        assert agents[0].framework == "crewai"
        assert agents[0].metadata["agent_count"] == 2
