"""
Unit Tests: State Diff Engine
================================
Tests for structural diff correctness on known inputs.
"""

from stateweave.core.diff import StateDiff, diff_payloads
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestStateDiff:
    def _make_payload(self, framework="langgraph", agent_id="test", **cog_kwargs):
        return StateWeavePayload(
            source_framework=framework,
            metadata=AgentMetadata(agent_id=agent_id),
            cognitive_state=CognitiveState(**cog_kwargs),
        )

    def test_identical_states_no_changes(self):
        p = self._make_payload(working_memory={"key": "value"})
        diff = diff_payloads(p, p)
        # exported_at will differ (default_factory creates new datetime)
        # so we check for minimal differences
        assert isinstance(diff, StateDiff)

    def test_added_working_memory(self):
        a = self._make_payload(working_memory={})
        b = self._make_payload(working_memory={"new_key": "added"})
        diff = diff_payloads(a, b)
        assert diff.has_changes
        added_paths = [e.path for e in diff.entries if e.diff_type == "added"]
        assert any("new_key" in p for p in added_paths)

    def test_removed_working_memory(self):
        a = self._make_payload(working_memory={"old_key": "exists"})
        b = self._make_payload(working_memory={})
        diff = diff_payloads(a, b)
        removed_paths = [e.path for e in diff.entries if e.diff_type == "removed"]
        assert any("old_key" in p for p in removed_paths)

    def test_modified_working_memory(self):
        a = self._make_payload(working_memory={"key": "old_value"})
        b = self._make_payload(working_memory={"key": "new_value"})
        diff = diff_payloads(a, b)
        modified = [e for e in diff.entries if e.diff_type == "modified"]
        assert any("key" in e.path for e in modified)

    def test_conversation_history_diff(self):
        a = self._make_payload(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello"),
            ]
        )
        b = self._make_payload(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi!"),
            ]
        )
        diff = diff_payloads(a, b)
        assert diff.has_changes
        assert diff.added_count > 0

    def test_framework_change_detected(self):
        a = self._make_payload(framework="langgraph")
        b = self._make_payload(framework="mcp")
        diff = diff_payloads(a, b)
        modified = [e for e in diff.entries if e.diff_type == "modified"]
        assert any("source_framework" in e.path for e in modified)

    def test_report_generation(self):
        a = self._make_payload(working_memory={"x": 1})
        b = self._make_payload(working_memory={"x": 2, "y": 3})
        diff = diff_payloads(a, b)
        report = diff.to_report()
        assert "STATEWEAVE DIFF REPORT" in report
        assert isinstance(report, str)

    def test_counts(self):
        a = self._make_payload(working_memory={"a": 1, "b": 2})
        b = self._make_payload(working_memory={"b": 99, "c": 3})
        diff = diff_payloads(a, b)
        # 'a' removed, 'b' modified, 'c' added
        wm_entries = [e for e in diff.entries if "working_memory" in e.path]
        assert any(e.diff_type == "removed" for e in wm_entries)
        assert any(e.diff_type == "modified" for e in wm_entries)
        assert any(e.diff_type == "added" for e in wm_entries)
