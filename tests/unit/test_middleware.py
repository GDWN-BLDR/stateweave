"""Tests for auto-checkpoint middleware."""

import shutil
import tempfile
import unittest

from stateweave.middleware.auto_checkpoint import (
    CheckpointMiddleware,
    CheckpointStrategy,
    auto_checkpoint,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload(agent_id="test-agent", messages=3, task="default"):
    history = [
        Message(
            role=MessageRole.HUMAN if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
        )
        for i in range(messages)
    ]
    return StateWeavePayload(
        source_framework="langgraph",
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=history,
            working_memory={"current_task": task},
        ),
    )


class TestCheckpointMiddleware(unittest.TestCase):
    """Test CheckpointMiddleware."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_record_returns_false_before_threshold(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=5,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        self.assertFalse(mw.record(payload))
        self.assertEqual(mw.step_count, 1)

    def test_record_returns_true_at_threshold(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=3,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)  # step 1
        mw.record(payload)  # step 2
        result = mw.record(payload)  # step 3 — checkpoint
        self.assertTrue(result)
        self.assertEqual(mw.step_count, 3)

    def test_force_checkpoint(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=100,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        result = mw.record(payload, force=True)
        self.assertTrue(result)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_context_manager(self):
        payload = _make_payload()
        with CheckpointMiddleware(
            agent_id="test",
            every_n_steps=2,
            store_dir=self.tmpdir,
        ) as mw:
            mw.record(payload)
            mw.record(payload)  # checkpoint here
        self.assertEqual(mw.step_count, 2)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_checkpoint_count_increments(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=1,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)
        mw.record(payload)
        mw.record(payload)
        self.assertEqual(mw.checkpoint_count, 3)


class TestOnSignificantDeltaStrategy(unittest.TestCase):
    """Test ON_SIGNIFICANT_DELTA strategy."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_first_record_always_checkpoints(self):
        """First call should always checkpoint (no baseline to compare against)."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.ON_SIGNIFICANT_DELTA,
            delta_threshold=3,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        result = mw.record(payload)
        self.assertTrue(result)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_identical_state_skips_checkpoint(self):
        """If state hasn't changed, no checkpoint should fire."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.ON_SIGNIFICANT_DELTA,
            delta_threshold=1,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)  # first — always checkpoints
        result = mw.record(payload)  # identical — should skip
        self.assertFalse(result)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_significant_change_triggers_checkpoint(self):
        """Changes exceeding threshold should trigger a checkpoint."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.ON_SIGNIFICANT_DELTA,
            delta_threshold=2,
            store_dir=self.tmpdir,
        )
        payload1 = _make_payload(task="research")
        mw.record(payload1)  # first — checkpoints

        # Create payload with significant changes
        payload2 = _make_payload(messages=5, task="analysis")
        result = mw.record(payload2)
        self.assertTrue(result)
        self.assertEqual(mw.checkpoint_count, 2)

    def test_minor_change_below_threshold_skips(self):
        """Changes below the threshold should not trigger a checkpoint."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.ON_SIGNIFICANT_DELTA,
            delta_threshold=100,  # Very high threshold
            store_dir=self.tmpdir,
        )
        payload1 = _make_payload(task="research")
        mw.record(payload1)  # first — checkpoints

        payload2 = _make_payload(task="analysis")  # small change
        result = mw.record(payload2)
        self.assertFalse(result)
        self.assertEqual(mw.checkpoint_count, 1)


class TestManualOnlyStrategy(unittest.TestCase):
    """Test MANUAL_ONLY strategy."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_auto_checkpoints(self):
        """Records should never auto-checkpoint in MANUAL_ONLY mode."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.MANUAL_ONLY,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        for _ in range(20):
            result = mw.record(payload)
            self.assertFalse(result)
        self.assertEqual(mw.checkpoint_count, 0)

    def test_force_still_works(self):
        """force=True should still create a checkpoint in MANUAL_ONLY mode."""
        mw = CheckpointMiddleware(
            agent_id="test",
            strategy=CheckpointStrategy.MANUAL_ONLY,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        result = mw.record(payload, force=True)
        self.assertTrue(result)
        self.assertEqual(mw.checkpoint_count, 1)


class TestCheckpointOverheadInstrumentation(unittest.TestCase):
    """Test timing instrumentation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_overhead_zero_before_checkpoints(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=100,
            store_dir=self.tmpdir,
        )
        self.assertEqual(mw.checkpoint_overhead_ms, 0.0)

    def test_overhead_positive_after_checkpoint(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=1,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)
        self.assertGreater(mw.checkpoint_overhead_ms, 0.0)

    def test_overhead_is_average(self):
        mw = CheckpointMiddleware(
            agent_id="test",
            every_n_steps=1,
            store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)
        mw.record(payload)
        mw.record(payload)
        # Should be average of 3 checkpoints
        self.assertGreater(mw.checkpoint_overhead_ms, 0.0)
        self.assertEqual(mw._checkpoint_invocations, 3)


class TestAutoCheckpointDecorator(unittest.TestCase):
    """Test @auto_checkpoint decorator."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_decorator_wraps_function(self):
        @auto_checkpoint(every_n_steps=2, store_dir=self.tmpdir)
        def my_func(payload):
            return payload

        payload = _make_payload()
        result = my_func(payload)
        self.assertIsInstance(result, StateWeavePayload)

    def test_decorator_auto_checkpoints(self):
        @auto_checkpoint(every_n_steps=2, store_dir=self.tmpdir)
        def process(payload):
            return payload

        payload = _make_payload()
        process(payload)  # step 1
        process(payload)  # step 2 — checkpoint

        self.assertEqual(process.middleware.step_count, 2)
        self.assertEqual(process.middleware.checkpoint_count, 1)

    def test_decorator_preserves_function_name(self):
        @auto_checkpoint(every_n_steps=5, store_dir=self.tmpdir)
        def my_agent_function(payload):
            return payload

        self.assertEqual(my_agent_function.__name__, "my_agent_function")

    def test_decorator_non_payload_return_no_crash(self):
        @auto_checkpoint(every_n_steps=1, store_dir=self.tmpdir)
        def returns_string(x):
            return "not a payload"

        result = returns_string("input")
        self.assertEqual(result, "not a payload")
        # No crash, no checkpoint (return isn't a StateWeavePayload)
        self.assertEqual(returns_string.middleware.checkpoint_count, 0)

    def test_decorator_with_delta_strategy(self):
        @auto_checkpoint(
            strategy="on_significant_delta",
            delta_threshold=2,
            store_dir=self.tmpdir,
        )
        def smart_process(payload):
            return payload

        payload1 = _make_payload(task="research")
        smart_process(payload1)  # first — checkpoints
        self.assertEqual(smart_process.middleware.checkpoint_count, 1)

        smart_process(payload1)  # identical — skips
        self.assertEqual(smart_process.middleware.checkpoint_count, 1)

    def test_decorator_with_manual_strategy(self):
        @auto_checkpoint(strategy="manual_only", store_dir=self.tmpdir)
        def manual_process(payload):
            return payload

        payload = _make_payload()
        manual_process(payload)
        manual_process(payload)
        manual_process(payload)
        self.assertEqual(manual_process.middleware.checkpoint_count, 0)


if __name__ == "__main__":
    unittest.main()
