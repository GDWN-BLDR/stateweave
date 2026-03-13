"""Tests for auto-checkpoint middleware."""

import shutil
import tempfile
import unittest

from stateweave.middleware.auto_checkpoint import (
    CheckpointMiddleware,
    auto_checkpoint,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload(agent_id="test-agent", messages=3):
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
            working_memory={},
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
            agent_id="test", every_n_steps=5, store_dir=self.tmpdir,
        )
        payload = _make_payload()
        self.assertFalse(mw.record(payload))
        self.assertEqual(mw.step_count, 1)

    def test_record_returns_true_at_threshold(self):
        mw = CheckpointMiddleware(
            agent_id="test", every_n_steps=3, store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)  # step 1
        mw.record(payload)  # step 2
        result = mw.record(payload)  # step 3 — checkpoint
        self.assertTrue(result)
        self.assertEqual(mw.step_count, 3)

    def test_force_checkpoint(self):
        mw = CheckpointMiddleware(
            agent_id="test", every_n_steps=100, store_dir=self.tmpdir,
        )
        payload = _make_payload()
        result = mw.record(payload, force=True)
        self.assertTrue(result)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_context_manager(self):
        payload = _make_payload()
        with CheckpointMiddleware(
            agent_id="test", every_n_steps=2, store_dir=self.tmpdir,
        ) as mw:
            mw.record(payload)
            mw.record(payload)  # checkpoint here
        self.assertEqual(mw.step_count, 2)
        self.assertEqual(mw.checkpoint_count, 1)

    def test_checkpoint_count_increments(self):
        mw = CheckpointMiddleware(
            agent_id="test", every_n_steps=1, store_dir=self.tmpdir,
        )
        payload = _make_payload()
        mw.record(payload)
        mw.record(payload)
        mw.record(payload)
        self.assertEqual(mw.checkpoint_count, 3)


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


if __name__ == "__main__":
    unittest.main()
