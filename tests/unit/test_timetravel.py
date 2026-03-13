"""Tests for Agent Time Travel — checkpoint, history, rollback, branch, diff."""

import os
import shutil
import tempfile
import unittest

from stateweave.core.timetravel import (
    CheckpointMetadata,
    CheckpointHistory,
    CheckpointStore,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload(
    agent_id: str = "test-agent",
    framework: str = "langgraph",
    messages: int = 3,
    memory: dict = None,
) -> StateWeavePayload:
    """Create a test payload with configurable state."""
    history = [
        Message(
            role=MessageRole.HUMAN if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
        )
        for i in range(messages)
    ]
    return StateWeavePayload(
        source_framework=framework,
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=history,
            working_memory=memory or {},
        ),
    )


class TestCheckpointMetadata(unittest.TestCase):
    """Test checkpoint metadata serialization."""

    def test_to_dict(self):
        cp = CheckpointMetadata(
            version=1,
            hash="abc123",
            agent_id="test",
            framework="langgraph",
            created_at="2026-03-13T00:00:00",
            message_count=5,
            working_memory_keys=2,
            label="initial",
        )
        d = cp.to_dict()
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["hash"], "abc123")
        self.assertEqual(d["label"], "initial")

    def test_from_dict(self):
        data = {
            "version": 3,
            "hash": "xyz789",
            "agent_id": "test-2",
            "framework": "crewai",
            "created_at": "2026-03-13T01:00:00",
            "message_count": 10,
            "working_memory_keys": 3,
            "branch": "experiment",
        }
        cp = CheckpointMetadata.from_dict(data)
        self.assertEqual(cp.version, 3)
        self.assertEqual(cp.branch, "experiment")


class TestCheckpointStore(unittest.TestCase):
    """Test the full checkpoint store lifecycle."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = CheckpointStore(store_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_creates_version(self):
        payload = _make_payload()
        cp = self.store.checkpoint(payload)
        self.assertEqual(cp.version, 1)
        self.assertEqual(cp.agent_id, "test-agent")
        self.assertEqual(cp.framework, "langgraph")
        self.assertEqual(cp.message_count, 3)

    def test_checkpoint_increments_version(self):
        p1 = _make_payload(messages=3)
        p2 = _make_payload(messages=5)
        cp1 = self.store.checkpoint(p1)
        cp2 = self.store.checkpoint(p2)
        self.assertEqual(cp1.version, 1)
        self.assertEqual(cp2.version, 2)

    def test_history_returns_all_versions(self):
        for i in range(5):
            self.store.checkpoint(_make_payload(messages=i + 1))

        history = self.store.history("test-agent")
        self.assertEqual(history.version_count, 5)
        self.assertEqual(history.latest.version, 5)

    def test_rollback_restores_state(self):
        p1 = _make_payload(messages=3, memory={"key": "v1"})
        p2 = _make_payload(messages=5, memory={"key": "v2"})
        self.store.checkpoint(p1)
        self.store.checkpoint(p2)

        restored = self.store.rollback("test-agent", 1)
        self.assertEqual(len(restored.cognitive_state.conversation_history), 3)
        self.assertEqual(restored.cognitive_state.working_memory["key"], "v1")

    def test_rollback_invalid_version_raises(self):
        self.store.checkpoint(_make_payload())
        with self.assertRaises(ValueError):
            self.store.rollback("test-agent", 99)

    def test_branch_creates_new_agent(self):
        p1 = _make_payload(messages=5, memory={"experiment": "data"})
        self.store.checkpoint(p1)

        cp = self.store.branch("test-agent", 1, "experiment-agent")
        self.assertEqual(cp.agent_id, "experiment-agent")
        self.assertIn("Branched from test-agent v1", cp.label)

        # Verify the branched state
        history = self.store.history("experiment-agent")
        self.assertEqual(history.version_count, 1)

    def test_diff_versions(self):
        p1 = _make_payload(messages=3, memory={"key": "v1"})
        p2 = _make_payload(messages=5, memory={"key": "v2"})
        self.store.checkpoint(p1)
        self.store.checkpoint(p2)

        diff = self.store.diff_versions("test-agent", 1, 2)
        self.assertTrue(diff.has_changes)

    def test_list_agents(self):
        self.store.checkpoint(_make_payload(agent_id="agent-1"))
        self.store.checkpoint(_make_payload(agent_id="agent-2"))

        agents = self.store.list_agents()
        self.assertIn("agent-1", agents)
        self.assertIn("agent-2", agents)

    def test_format_history(self):
        self.store.checkpoint(_make_payload(messages=3))
        self.store.checkpoint(_make_payload(messages=5))

        report = self.store.format_history("test-agent")
        self.assertIn("test-agent", report)
        self.assertIn("v  1", report)
        self.assertIn("v  2", report)

    def test_format_history_empty(self):
        report = self.store.format_history("nonexistent")
        self.assertIn("No checkpoints found", report)

    def test_content_addressable_hashing(self):
        """Same payload checkpointed twice should produce the same hash."""
        p1 = _make_payload(messages=3, memory={"key": "value"})
        from stateweave.core.delta import compute_payload_hash

        hash1 = compute_payload_hash(p1)
        hash2 = compute_payload_hash(p1)
        self.assertEqual(hash1, hash2)

    def test_different_content_different_hash(self):
        p1 = _make_payload(messages=3)
        p2 = _make_payload(messages=5)
        cp1 = self.store.checkpoint(p1, agent_id="a1")
        cp2 = self.store.checkpoint(p2, agent_id="a2")
        self.assertNotEqual(cp1.hash, cp2.hash)

    def test_parent_hash_chain(self):
        self.store.checkpoint(_make_payload(messages=1))
        self.store.checkpoint(_make_payload(messages=2))
        self.store.checkpoint(_make_payload(messages=3))

        history = self.store.history("test-agent")
        cp1 = history.get_version(1)
        cp2 = history.get_version(2)
        cp3 = history.get_version(3)

        self.assertIsNone(cp1.parent_hash)
        self.assertEqual(cp2.parent_hash, cp1.hash)
        self.assertEqual(cp3.parent_hash, cp2.hash)

    def test_checkpoint_with_label(self):
        cp = self.store.checkpoint(
            _make_payload(),
            label="before-experiment",
        )
        self.assertEqual(cp.label, "before-experiment")

    def test_checkpoint_with_branch(self):
        cp = self.store.checkpoint(
            _make_payload(),
            branch="experiment",
        )
        self.assertEqual(cp.branch, "experiment")

        history = self.store.history("test-agent")
        self.assertIn("experiment", history.branches)
        self.assertIn(1, history.branches["experiment"])


class TestCheckpointHistory(unittest.TestCase):
    """Test CheckpointHistory data structure."""

    def test_empty_history(self):
        h = CheckpointHistory(agent_id="test")
        self.assertIsNone(h.latest)
        self.assertEqual(h.version_count, 0)

    def test_get_version(self):
        h = CheckpointHistory(agent_id="test")
        cp = CheckpointMetadata(
            version=1, hash="abc", agent_id="test",
            framework="lg", created_at="now",
            message_count=0, working_memory_keys=0,
        )
        h.checkpoints.append(cp)
        self.assertEqual(h.get_version(1), cp)
        self.assertIsNone(h.get_version(99))

    def test_get_by_hash(self):
        h = CheckpointHistory(agent_id="test")
        cp = CheckpointMetadata(
            version=1, hash="abcdef123456", agent_id="test",
            framework="lg", created_at="now",
            message_count=0, working_memory_keys=0,
        )
        h.checkpoints.append(cp)
        self.assertEqual(h.get_by_hash("abcdef"), cp)
        self.assertIsNone(h.get_by_hash("zzz"))


if __name__ == "__main__":
    unittest.main()
