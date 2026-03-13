"""Tests for the playground API."""

import unittest

from stateweave.core.serializer import StateWeaveSerializer
from stateweave.playground.api import PlaygroundAPI
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload_dict(agent_id="test-agent", messages=2):
    payload = StateWeavePayload(
        source_framework="langgraph",
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content=f"msg-{i}") for i in range(messages)
            ],
            working_memory={"key": "value"},
        ),
    )
    serializer = StateWeaveSerializer()
    return serializer.to_dict(payload)


class TestPlaygroundAPI(unittest.TestCase):
    """Test playground API methods."""

    def setUp(self):
        self.api = PlaygroundAPI()

    def test_info(self):
        result = self.api.info()
        self.assertIn("version", result)
        self.assertIn("adapters", result)
        self.assertIsInstance(result["adapters"], list)
        self.assertGreater(result["adapter_count"], 0)

    def test_doctor(self):
        result = self.api.doctor()
        self.assertIn("healthy", result)
        self.assertIn("checks", result)
        self.assertIsInstance(result["checks"], list)

    def test_validate_valid_payload(self):
        payload_dict = _make_payload_dict()
        result = self.api.validate(payload_dict)
        self.assertTrue(result["valid"])
        self.assertEqual(result["agent_id"], "test-agent")
        self.assertEqual(result["messages"], 2)

    def test_validate_invalid_payload(self):
        result = self.api.validate({"not": "a payload"})
        self.assertFalse(result["valid"])
        self.assertIn("error", result)

    def test_checkpoint(self):
        payload_dict = _make_payload_dict()
        result = self.api.checkpoint(payload_dict, label="test-checkpoint")
        self.assertIn("version", result)
        self.assertIn("hash", result)
        self.assertEqual(result["label"], "test-checkpoint")

    def test_get_history(self):
        payload_dict = _make_payload_dict(agent_id="history-test")
        self.api.checkpoint(payload_dict, label="v1")
        self.api.checkpoint(payload_dict, label="v2")
        result = self.api.get_history("history-test")
        self.assertEqual(result["version_count"], 2)

    def test_diff(self):
        state_a = _make_payload_dict(messages=2)
        state_b = _make_payload_dict(messages=4)
        result = self.api.diff(state_a, state_b)
        self.assertIn("total_changes", result)
        self.assertIn("report", result)


if __name__ == "__main__":
    unittest.main()
