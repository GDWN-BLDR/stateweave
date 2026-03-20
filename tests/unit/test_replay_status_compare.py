"""Tests for stateweave replay, status, and compare CLI commands."""

import subprocess
import sys
import tempfile

from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.replay import ReplayEngine, ReplayResult
from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import Message, MessageRole


class TestReplayEngine:
    """Tests for the ReplayEngine."""

    def test_replay_no_checkpoints(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        engine = ReplayEngine(store)
        result = engine.replay("nonexistent")
        assert isinstance(result, ReplayResult)
        assert len(result.steps) == 0

    def test_replay_single_checkpoint(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("test-agent", num_messages=3)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="test-agent", label="v1")

        engine = ReplayEngine(store)
        result = engine.replay("test-agent")

        assert len(result.steps) == 1
        step = result.steps[0]
        assert step.version == 1
        assert step.label == "v1"
        assert step.message_count == 3
        assert step.confidence == 0.9

    def test_replay_multiple_checkpoints_with_changes(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("test-agent", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="test-agent", label="initial")

        # Modify and checkpoint again
        payload.cognitive_state.conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content="New response")
        )
        payload.cognitive_state.working_memory["confidence"] = 0.5
        payload.cognitive_state.working_memory["new_key"] = "value"
        store.checkpoint(payload, agent_id="test-agent", label="after-change")

        engine = ReplayEngine(store)
        result = engine.replay("test-agent")

        assert len(result.steps) == 2
        assert result.steps[0].confidence == 0.9
        assert result.steps[1].confidence == 0.5
        assert result.steps[1].messages_added >= 1
        assert "new_key" in result.steps[1].memory_added
        assert "confidence" in result.steps[1].memory_changed

    def test_replay_confidence_drop_alert(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("test-agent", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.95
        store.checkpoint(payload, agent_id="test-agent")

        payload.cognitive_state.working_memory["confidence"] = 0.2
        store.checkpoint(payload, agent_id="test-agent")

        engine = ReplayEngine(store)
        result = engine.replay("test-agent")

        # Second step should have a confidence drop alert
        assert len(result.steps[1].alerts) >= 1
        assert any("Confidence dropped" in a for a in result.steps[1].alerts)

    def test_replay_version_range(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("test-agent", num_messages=2)

        for i in range(5):
            payload.cognitive_state.working_memory[f"step_{i}"] = i
            store.checkpoint(payload, agent_id="test-agent", label=f"step-{i}")

        engine = ReplayEngine(store)
        result = engine.replay("test-agent", from_version=2, to_version=4)

        assert len(result.steps) == 3  # v2, v3, v4

    def test_biggest_change_step(self):
        store = CheckpointStore(store_dir=tempfile.mkdtemp())
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("test-agent", num_messages=2)
        store.checkpoint(payload, agent_id="test-agent")

        # Add many changes
        for i in range(5):
            payload.cognitive_state.working_memory[f"big_change_{i}"] = f"value_{i}"
        payload.cognitive_state.conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content="Big change")
        )
        store.checkpoint(payload, agent_id="test-agent")

        engine = ReplayEngine(store)
        result = engine.replay("test-agent")
        biggest = result.biggest_change_step
        assert biggest is not None
        assert biggest.version == 2


class TestReplayStatusCompareCLI:
    """Tests for replay/status/compare CLI output."""

    def test_replay_cli_no_checkpoints(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "replay",
                "nonexistent",
                "--store-dir",
                tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
        )
        assert "No checkpoints" in result.stdout

    def test_status_cli_empty_store(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "status", "--store-dir", tempfile.mkdtemp()],
            capture_output=True,
            text=True,
        )
        assert "No" in result.stdout  # "No agents tracked" or "No .stateweave"

    def test_compare_cli_invalid_ref(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "compare",
                "bad-ref",
                "also-bad",
                "--store-dir",
                tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
        )
        assert "Invalid ref" in result.stdout or "⚠" in result.stdout

    def test_replay_cli_with_data(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("cli-test", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.85
        store.checkpoint(payload, agent_id="cli-test", label="v1")

        payload.cognitive_state.working_memory["confidence"] = 0.4
        store.checkpoint(payload, agent_id="cli-test", label="degraded")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "replay",
                "cli-test",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "Replaying" in result.stdout
        assert "cli-test" in result.stdout
        assert "v1" in result.stdout

    def test_status_cli_with_data(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("status-test", num_messages=3)
        store.checkpoint(payload, agent_id="status-test")

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "status", "--store-dir", store_dir],
            capture_output=True,
            text=True,
        )
        assert "StateWeave Status" in result.stdout
        assert "status-test" in result.stdout

    def test_compare_cli_with_data(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("cmp-test", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="cmp-test", label="good")

        payload.cognitive_state.working_memory["confidence"] = 0.3
        payload.cognitive_state.working_memory["risk"] = "HIGH"
        store.checkpoint(payload, agent_id="cmp-test", label="bad")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "compare",
                "cmp-test:v1",
                "cmp-test:v2",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "Side-by-Side" in result.stdout
        assert "Messages" in result.stdout
