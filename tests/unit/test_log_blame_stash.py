"""Tests for stateweave log, blame, stash, and pop CLI commands."""

import subprocess
import sys
import tempfile

from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.timetravel import CheckpointStore


class TestLogCLI:
    """Tests for stateweave log."""

    def test_log_with_data(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("log-test", num_messages=3)
        payload.cognitive_state.working_memory["confidence"] = 0.85
        store.checkpoint(payload, agent_id="log-test", label="initial")
        store.checkpoint(payload, agent_id="log-test", label="updated")

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "log", "log-test", "--store-dir", store_dir],
            capture_output=True,
            text=True,
        )
        assert "log-test" in result.stdout
        assert "initial" in result.stdout
        assert "updated" in result.stdout
        assert "2 checkpoint" in result.stdout

    def test_log_no_checkpoints(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "log",
                "nonexistent",
                "--store-dir",
                tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
        )
        assert "No checkpoints" in result.stdout

    def test_log_with_confidence_bar(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("bar-test", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="bar-test", label="high-conf")

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "log", "bar-test", "--store-dir", store_dir],
            capture_output=True,
            text=True,
        )
        assert "█" in result.stdout  # Confidence bar
        assert "90%" in result.stdout


class TestBlameCLI:
    """Tests for stateweave blame."""

    def test_blame_finds_key(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("blame-test", num_messages=2)
        store.checkpoint(payload, agent_id="blame-test", label="v1")

        payload.cognitive_state.working_memory["special_key"] = "hello"
        store.checkpoint(payload, agent_id="blame-test", label="v2")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "blame",
                "blame-test",
                "special_key",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "special_key" in result.stdout
        assert "Introduced" in result.stdout
        assert "v2" in result.stdout

    def test_blame_key_not_found(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("blame-test2", num_messages=2)
        store.checkpoint(payload, agent_id="blame-test2")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "blame",
                "blame-test2",
                "nonexistent_key",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "not found" in result.stdout

    def test_blame_value_history(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("blame-hist", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="blame-hist", label="high")

        payload.cognitive_state.working_memory["confidence"] = 0.3
        store.checkpoint(payload, agent_id="blame-hist", label="low")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "blame",
                "blame-hist",
                "confidence",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "History:" in result.stdout
        assert "0.9" in result.stdout
        assert "0.3" in result.stdout


class TestStashPopCLI:
    """Tests for stateweave stash and pop."""

    def test_stash_and_pop(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()

        # Create and checkpoint
        payload = adapter.create_sample_payload("stash-test", num_messages=3)
        payload.cognitive_state.working_memory["confidence"] = 0.95
        store.checkpoint(payload, agent_id="stash-test", label="good-state")

        # Add more state
        payload.cognitive_state.working_memory["confidence"] = 0.2
        payload.cognitive_state.working_memory["bad_key"] = "trouble"
        store.checkpoint(payload, agent_id="stash-test", label="bad-state")

        # Stash v1 (good state)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "stash",
                "stash-test",
                "--name",
                "safe-point",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "Stashed" in result.stdout

        # Pop (restore to v2 which is latest, stash was at v2 too)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "pop",
                "stash-test",
                "--name",
                "safe-point",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "Popped" in result.stdout
        assert "removed" in result.stdout

    def test_pop_no_stash(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "pop",
                "nonexistent",
                "--name",
                "nope",
                "--store-dir",
                tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
        )
        assert "No stash" in result.stdout
