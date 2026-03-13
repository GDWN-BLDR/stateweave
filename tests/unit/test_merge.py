"""
Unit Tests: State Merge Engine (CRDT Foundation)
==================================================
Tests for merge_payloads with Last-Writer-Wins, Union,
and Manual conflict resolution policies.
"""

from datetime import datetime

import pytest

from stateweave.core.merge import (
    ConflictResolutionPolicy,
    MergeConflictError,
    MergeResult,
    merge_payloads,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    GoalNode,
    Message,
    MessageRole,
    StateWeavePayload,
    ToolResult,
)


@pytest.fixture
def payload_a():
    return StateWeavePayload(
        source_framework="langgraph",
        exported_at=datetime(2026, 3, 13, 10, 0, 0),
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello from Agent A"),
                Message(role=MessageRole.ASSISTANT, content="Agent A response"),
            ],
            working_memory={
                "shared_key": "value_from_a",
                "only_in_a": "a_data",
                "confidence": 0.7,
            },
            goal_tree={
                "goal_1": GoalNode(goal_id="goal_1", description="Shared goal", status="pending"),
                "goal_a": GoalNode(goal_id="goal_a", description="A's goal", status="in_progress"),
            },
            tool_results_cache={
                "search": ToolResult(
                    tool_name="search", arguments={}, result={"count": 5}, success=True
                ),
            },
        ),
        metadata=AgentMetadata(agent_id="agent-a", agent_name="Agent A"),
    )


@pytest.fixture
def payload_b():
    return StateWeavePayload(
        source_framework="mcp",
        exported_at=datetime(2026, 3, 13, 11, 0, 0),  # B is newer
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hello from Agent B"),
                Message(role=MessageRole.ASSISTANT, content="Agent B response"),
            ],
            working_memory={
                "shared_key": "value_from_b",
                "only_in_b": "b_data",
                "confidence": 0.9,
            },
            goal_tree={
                "goal_1": GoalNode(goal_id="goal_1", description="Shared goal", status="completed"),
                "goal_b": GoalNode(goal_id="goal_b", description="B's goal", status="pending"),
            },
            tool_results_cache={
                "search": ToolResult(
                    tool_name="search", arguments={}, result={"count": 10}, success=True
                ),
                "analyze": ToolResult(tool_name="analyze", arguments={}, result={}, success=True),
            },
        ),
        metadata=AgentMetadata(agent_id="agent-b", agent_name="Agent B"),
    )


class TestMergeLastWriterWins:
    def test_basic_merge(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        assert isinstance(result, MergeResult)
        assert result.payload is not None

    def test_newer_wins_for_conflicts(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        # B is newer, so B's value should win
        wm = result.payload.cognitive_state.working_memory
        assert wm["shared_key"] == "value_from_b"
        assert wm["confidence"] == 0.9

    def test_unique_keys_preserved(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        wm = result.payload.cognitive_state.working_memory
        assert "only_in_a" in wm
        assert "only_in_b" in wm

    def test_conflicts_counted(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        assert result.conflicts_resolved >= 2  # shared_key + confidence

    def test_policy_recorded(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        assert result.policy_used == ConflictResolutionPolicy.LAST_WRITER_WINS


class TestMergeUnion:
    def test_union_merge(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.UNION)
        assert result.payload is not None

    def test_messages_unioned(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.UNION)
        msgs = result.payload.cognitive_state.conversation_history
        # Should have unique messages from both
        contents = [m.content for m in msgs]
        assert "Hello from Agent A" in contents
        assert "Hello from Agent B" in contents

    def test_goal_trees_unioned(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.UNION)
        goals = result.payload.cognitive_state.goal_tree
        assert "goal_a" in goals
        assert "goal_b" in goals
        assert "goal_1" in goals

    def test_shared_goal_updated(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.UNION)
        goals = result.payload.cognitive_state.goal_tree
        # goal_1: B has "completed" which is more progress than A's "pending"
        assert goals["goal_1"].status == "completed"

    def test_tool_results_unioned(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.UNION)
        tools = result.payload.cognitive_state.tool_results_cache
        assert "analyze" in tools  # Only in B


class TestMergeManual:
    def test_raises_on_conflict(self, payload_a, payload_b):
        with pytest.raises(MergeConflictError) as exc_info:
            merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.MANUAL)
        assert len(exc_info.value.conflicts) >= 1

    def test_no_conflict_succeeds(self):
        """Two payloads with no conflicting working memory should merge fine."""
        p1 = StateWeavePayload(
            source_framework="a",
            metadata=AgentMetadata(agent_id="1", agent_name="1"),
            cognitive_state=CognitiveState(working_memory={"key_a": "val_a"}),
        )
        p2 = StateWeavePayload(
            source_framework="b",
            metadata=AgentMetadata(agent_id="2", agent_name="2"),
            cognitive_state=CognitiveState(working_memory={"key_b": "val_b"}),
        )
        result = merge_payloads(p1, p2, ConflictResolutionPolicy.MANUAL)
        wm = result.payload.cognitive_state.working_memory
        assert wm["key_a"] == "val_a"
        assert wm["key_b"] == "val_b"


class TestMergeAuditTrail:
    def test_audit_trails_merged(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        trail = result.payload.audit_trail
        # Should have the merge operation entry
        merge_entries = [e for e in trail if e.details.get("operation") == "merge"]
        assert len(merge_entries) >= 1

    def test_source_framework_combined(self, payload_a, payload_b):
        result = merge_payloads(payload_a, payload_b, ConflictResolutionPolicy.LAST_WRITER_WINS)
        assert "langgraph" in result.payload.source_framework
        assert "mcp" in result.payload.source_framework


class TestMergeEdgeCases:
    def test_merge_identical_payloads(self, payload_a):
        result = merge_payloads(payload_a, payload_a, ConflictResolutionPolicy.LAST_WRITER_WINS)
        assert result.conflicts_resolved == 0

    def test_merge_empty_payloads(self):
        p1 = StateWeavePayload(
            source_framework="a",
            metadata=AgentMetadata(agent_id="1", agent_name="1"),
        )
        p2 = StateWeavePayload(
            source_framework="b",
            metadata=AgentMetadata(agent_id="2", agent_name="2"),
        )
        result = merge_payloads(p1, p2, ConflictResolutionPolicy.UNION)
        assert result.payload is not None
        assert result.conflicts_resolved == 0
