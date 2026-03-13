"""Tests for A2A Bridge — Agent-to-Agent Protocol integration."""

import unittest

from stateweave.a2a.bridge import (
    STATEWEAVE_A2A_SKILL_ID,
    STATEWEAVE_MIME_TYPE,
    A2AAgentCapabilities,
    A2ABridge,
)
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload(
    agent_id: str = "source-agent",
    framework: str = "langgraph",
    messages: int = 5,
) -> StateWeavePayload:
    """Create a test payload."""
    history = [
        Message(
            role=MessageRole.HUMAN if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}: {'Hello' if i % 2 == 0 else 'Response'}",
        )
        for i in range(messages)
    ]
    return StateWeavePayload(
        source_framework=framework,
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=history,
            working_memory={"current_topic": "climate research"},
        ),
    )


class TestA2ABridge(unittest.TestCase):
    """Test the A2A bridge functionality."""

    def setUp(self):
        self.bridge = A2ABridge()
        self.payload = _make_payload()

    def test_create_transfer_artifact(self):
        artifact = self.bridge.create_transfer_artifact(self.payload)
        self.assertIn("name", artifact)
        self.assertIn("parts", artifact)
        self.assertEqual(len(artifact["parts"]), 1)
        self.assertEqual(artifact["parts"][0]["mimeType"], STATEWEAVE_MIME_TYPE)

    def test_transfer_artifact_contains_payload_data(self):
        artifact = self.bridge.create_transfer_artifact(self.payload)
        data = artifact["parts"][0]["data"]
        self.assertIn("source_framework", data)
        self.assertEqual(data["source_framework"], "langgraph")

    def test_transfer_artifact_metadata(self):
        artifact = self.bridge.create_transfer_artifact(self.payload)
        meta = artifact["parts"][0]["metadata"]
        self.assertEqual(meta["source_framework"], "langgraph")
        self.assertEqual(meta["agent_id"], "source-agent")
        self.assertEqual(meta["message_count"], 5)

    def test_transfer_artifact_custom_name(self):
        artifact = self.bridge.create_transfer_artifact(self.payload, artifact_name="my-state")
        self.assertEqual(artifact["name"], "my-state")

    def test_extract_payload_from_parts(self):
        # Create artifact, extract its parts, then extract payload
        artifact = self.bridge.create_transfer_artifact(self.payload)
        parts = artifact["parts"]

        extracted = self.bridge.extract_payload(parts)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.source_framework, "langgraph")
        self.assertEqual(extracted.metadata.agent_id, "source-agent")
        self.assertEqual(len(extracted.cognitive_state.conversation_history), 5)

    def test_extract_payload_no_stateweave_part(self):
        parts = [
            {"type": "text", "text": "Hello"},
            {"type": "data", "mimeType": "application/json", "data": {}},
        ]
        result = self.bridge.extract_payload(parts)
        self.assertIsNone(result)

    def test_round_trip_artifact_to_payload(self):
        """Create artifact → extract → verify content matches."""
        artifact = self.bridge.create_transfer_artifact(self.payload)
        extracted = self.bridge.extract_payload(artifact["parts"])

        # Verify messages content matches
        original_msgs = {m.content for m in self.payload.cognitive_state.conversation_history}
        extracted_msgs = {m.content for m in extracted.cognitive_state.conversation_history}
        self.assertEqual(original_msgs, extracted_msgs)

        # Verify working memory matches
        self.assertEqual(
            extracted.cognitive_state.working_memory["current_topic"],
            "climate research",
        )

    def test_create_handoff_task(self):
        task = self.bridge.create_handoff_task(
            self.payload,
            target_agent_url="http://agent-b.example.com/a2a",
        )
        self.assertEqual(task["jsonrpc"], "2.0")
        self.assertEqual(task["method"], "tasks/send")
        self.assertIn("params", task)

        message = task["params"]["message"]
        self.assertEqual(message["role"], "user")
        self.assertEqual(len(message["parts"]), 2)

        # First part is text description
        self.assertEqual(message["parts"][0]["type"], "text")
        self.assertIn("langgraph", message["parts"][0]["text"])

        # Second part is the StateWeave payload
        self.assertEqual(message["parts"][1]["mimeType"], STATEWEAVE_MIME_TYPE)

    def test_create_handoff_task_custom_description(self):
        task = self.bridge.create_handoff_task(
            self.payload,
            target_agent_url="http://example.com",
            task_description="Please continue the climate research",
        )
        text_part = task["params"]["message"]["parts"][0]
        self.assertEqual(text_part["text"], "Please continue the climate research")

    def test_handoff_task_metadata(self):
        task = self.bridge.create_handoff_task(
            self.payload,
            target_agent_url="http://example.com",
        )
        meta = task["params"]["metadata"]
        self.assertTrue(meta["stateweave_transfer"])
        self.assertEqual(meta["source_framework"], "langgraph")
        self.assertEqual(meta["source_agent_id"], "source-agent")


class TestA2AAgentCapabilities(unittest.TestCase):
    """Test A2A AgentCard capability generation."""

    def test_default_capabilities(self):
        caps = A2AAgentCapabilities()
        self.assertTrue(caps.can_export)
        self.assertTrue(caps.can_import)
        self.assertTrue(caps.encryption_supported)

    def test_to_agent_card_skill(self):
        caps = A2AAgentCapabilities(
            supported_frameworks=["langgraph", "crewai"],
            stateweave_version="0.3.0",
        )
        skill = caps.to_agent_card_skill()
        self.assertEqual(skill["id"], STATEWEAVE_A2A_SKILL_ID)
        self.assertIn("state-transfer", skill["tags"])
        self.assertEqual(
            skill["metadata"]["stateweave.frameworks"],
            ["langgraph", "crewai"],
        )
        self.assertEqual(skill["metadata"]["stateweave.version"], "0.3.0")

    def test_get_agent_capabilities(self):
        caps = A2ABridge.get_agent_capabilities(supported_frameworks=["langgraph", "mcp"])
        self.assertIsInstance(caps, A2AAgentCapabilities)
        self.assertEqual(caps.supported_frameworks, ["langgraph", "mcp"])

    def test_get_agent_capabilities_auto_detect(self):
        caps = A2ABridge.get_agent_capabilities()
        self.assertIsInstance(caps, A2AAgentCapabilities)
        self.assertTrue(len(caps.supported_frameworks) >= 10)


class TestMIMEType(unittest.TestCase):
    """Test MIME type constants."""

    def test_mime_type_is_vendor(self):
        self.assertTrue(STATEWEAVE_MIME_TYPE.startswith("application/vnd."))

    def test_mime_type_includes_json(self):
        self.assertTrue(STATEWEAVE_MIME_TYPE.endswith("+json"))


if __name__ == "__main__":
    unittest.main()
