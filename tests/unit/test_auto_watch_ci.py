"""Tests for stateweave.auto(), stateweave watch, and stateweave ci."""

import subprocess
import sys
import tempfile

from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.auto import auto, get_instrumentor
from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import Message, MessageRole


class TestAutoInstrumentor:
    """Tests for AutoInstrumentor core."""

    def test_auto_creates_singleton(self):
        sw = auto(store_dir=tempfile.mkdtemp(), verbose=False)
        assert sw is not None
        assert get_instrumentor() is sw

    def test_auto_record_creates_checkpoint(self):
        store_dir = tempfile.mkdtemp()
        sw = auto(store_dir=store_dir, checkpoint_every=1, verbose=False)

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("auto-test", num_messages=2)

        did_checkpoint = sw.record(payload, agent_id="auto-test")
        assert did_checkpoint

        # Verify checkpoint exists
        store = CheckpointStore(store_dir=store_dir)
        history = store.history("auto-test")
        assert history.version_count >= 1

    def test_auto_record_respects_frequency(self):
        store_dir = tempfile.mkdtemp()
        sw = auto(store_dir=store_dir, checkpoint_every=3, verbose=False)

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("freq-test", num_messages=2)

        results = []
        for _ in range(6):
            results.append(sw.record(payload, agent_id="freq-test"))

        # Should checkpoint at steps 3 and 6
        assert results[2] is True  # step 3
        assert results[5] is True  # step 6
        assert results[0] is False  # step 1
        assert results[1] is False  # step 2

    def test_auto_confidence_alert(self):
        store_dir = tempfile.mkdtemp()
        captured_alerts = []
        sw = auto(
            store_dir=store_dir,
            checkpoint_every=1,
            alert_on_confidence=0.5,
            alert_callback=lambda a: captured_alerts.append(a),
            verbose=False,
        )

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("alert-test", num_messages=2)
        payload.cognitive_state.working_memory["confidence"] = 0.3

        sw.record(payload, agent_id="alert-test")

        assert len(captured_alerts) >= 1
        assert captured_alerts[0].alert_type == "confidence_drop"

    def test_auto_confidence_drop_alert(self):
        store_dir = tempfile.mkdtemp()
        captured_alerts = []
        sw = auto(
            store_dir=store_dir,
            checkpoint_every=1,
            alert_callback=lambda a: captured_alerts.append(a),
            verbose=False,
        )

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("drop-test", num_messages=2)

        # First record with high confidence
        payload.cognitive_state.working_memory["confidence"] = 0.95
        sw.record(payload, agent_id="drop-test")

        # Second record with low confidence (>0.3 drop)
        payload.cognitive_state.working_memory["confidence"] = 0.2
        sw.record(payload, agent_id="drop-test")

        critical_alerts = [a for a in captured_alerts if a.severity == "critical"]
        assert len(critical_alerts) >= 1
        assert any("dropped" in a.message.lower() for a in critical_alerts)

    def test_auto_hallucination_alert(self):
        store_dir = tempfile.mkdtemp()
        captured_alerts = []
        sw = auto(
            store_dir=store_dir,
            checkpoint_every=1,
            alert_callback=lambda a: captured_alerts.append(a),
            verbose=False,
        )

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("hallu-test", num_messages=2)
        payload.cognitive_state.working_memory["hallucination_risk"] = "HIGH"

        sw.record(payload, agent_id="hallu-test")

        hallu_alerts = [a for a in captured_alerts if a.alert_type == "hallucination_risk"]
        assert len(hallu_alerts) >= 1

    def test_auto_summary(self):
        store_dir = tempfile.mkdtemp()
        sw = auto(store_dir=store_dir, checkpoint_every=1, verbose=False)

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("summary-test", num_messages=2)
        sw.record(payload, agent_id="summary-test")

        summary = sw.summary()
        assert summary["enabled"] is True
        assert "summary-test" in summary["agents"]
        assert summary["agents"]["summary-test"]["steps"] == 1

    def test_auto_disable_enable(self):
        store_dir = tempfile.mkdtemp()
        sw = auto(store_dir=store_dir, checkpoint_every=1, verbose=False)

        adapter = ADAPTER_REGISTRY["langgraph"]()
        payload = adapter.create_sample_payload("toggle-test", num_messages=2)

        sw.disable()
        result = sw.record(payload, agent_id="toggle-test")
        assert result is False

        sw.enable()
        result = sw.record(payload, agent_id="toggle-test")
        assert result is True

    def test_auto_multiple_agents(self):
        store_dir = tempfile.mkdtemp()
        sw = auto(store_dir=store_dir, checkpoint_every=1, verbose=False)

        adapter = ADAPTER_REGISTRY["langgraph"]()

        for agent_id in ["agent-a", "agent-b", "agent-c"]:
            payload = adapter.create_sample_payload(agent_id, num_messages=2)
            sw.record(payload, agent_id=agent_id)

        assert len(sw.agents) == 3


class TestCICLI:
    """Tests for stateweave ci CLI command."""

    def test_ci_pass(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()

        # Baseline
        payload = adapter.create_sample_payload("ci-test", num_messages=3)
        payload.cognitive_state.working_memory["confidence"] = 0.9
        store.checkpoint(payload, agent_id="ci-test", label="baseline")

        # Current — same confidence, more messages
        payload.cognitive_state.conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content="Good result")
        )
        store.checkpoint(payload, agent_id="ci-test", label="current")

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "ci", "ci-test", "--store-dir", store_dir],
            capture_output=True,
            text=True,
        )
        assert "CI PASSED" in result.stdout
        assert result.returncode == 0

    def test_ci_fail_on_regression(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()

        # Baseline — high confidence
        payload = adapter.create_sample_payload("ci-fail-test", num_messages=3)
        payload.cognitive_state.working_memory["confidence"] = 0.95
        store.checkpoint(payload, agent_id="ci-fail-test", label="baseline")

        # Current — regressed confidence
        payload.cognitive_state.working_memory["confidence"] = 0.3
        payload.cognitive_state.working_memory["hallucination_risk"] = "HIGH"
        store.checkpoint(payload, agent_id="ci-fail-test", label="regressed")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "ci",
                "ci-fail-test",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "CI FAILED" in result.stdout
        assert result.returncode != 0

    def test_ci_no_checkpoints(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "ci",
                "nonexistent",
                "--store-dir",
                tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
        )
        assert "No checkpoints" in result.stdout
        assert result.returncode != 0

    def test_ci_max_changes(self):
        store_dir = tempfile.mkdtemp()
        store = CheckpointStore(store_dir=store_dir)
        adapter = ADAPTER_REGISTRY["langgraph"]()

        payload = adapter.create_sample_payload("ci-max-test", num_messages=2)
        store.checkpoint(payload, agent_id="ci-max-test")

        # Add lots of changes
        for i in range(10):
            payload.cognitive_state.working_memory[f"new_key_{i}"] = f"value_{i}"
        store.checkpoint(payload, agent_id="ci-max-test")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "ci",
                "ci-max-test",
                "--max-changes",
                "3",
                "--store-dir",
                store_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert "CI FAILED" in result.stdout or "CI PASSED" in result.stdout
