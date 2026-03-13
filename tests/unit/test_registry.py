"""Tests for schema registry."""

import shutil
import tempfile
import unittest

from stateweave.registry.client import RegistryClient, RegistryEntry
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def _make_payload(agent_id="test-agent", framework="langgraph", messages=2):
    return StateWeavePayload(
        source_framework=framework,
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content=f"msg-{i}") for i in range(messages)
            ],
            working_memory={"task": "test"},
        ),
    )


class TestRegistryClient(unittest.TestCase):
    """Test schema registry client."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.client = RegistryClient(registry_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_publish(self):
        payload = _make_payload()
        entry = self.client.publish(
            "support-agent",
            payload,
            description="Customer support agent schema",
            tags=["support", "crewai"],
            author="test",
        )
        self.assertEqual(entry.name, "support-agent")
        self.assertIn("support", entry.tags)

    def test_get(self):
        payload = _make_payload()
        self.client.publish("my-schema", payload)
        result = self.client.get("my-schema")
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata.agent_id, "test-agent")

    def test_get_nonexistent(self):
        result = self.client.get("does-not-exist")
        self.assertIsNone(result)

    def test_get_entry(self):
        payload = _make_payload()
        self.client.publish("test-schema", payload, tags=["tag1"])
        entry = self.client.get_entry("test-schema")
        self.assertIsNotNone(entry)
        self.assertIn("tag1", entry.tags)

    def test_search_by_name(self):
        self.client.publish("customer-bot", _make_payload())
        self.client.publish("sales-agent", _make_payload())
        results = self.client.search("customer")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "customer-bot")

    def test_search_by_tag(self):
        self.client.publish("a", _make_payload(), tags=["production"])
        self.client.publish("b", _make_payload(), tags=["staging"])
        results = self.client.search("", tags=["production"])
        # search with empty query matches all, tag filter narrows
        self.assertTrue(any(r.name == "a" for r in results))

    def test_list_all(self):
        self.client.publish("schema-1", _make_payload())
        self.client.publish("schema-2", _make_payload())
        results = self.client.list_all()
        self.assertEqual(len(results), 2)

    def test_delete(self):
        self.client.publish("to-delete", _make_payload())
        deleted = self.client.delete("to-delete")
        self.assertTrue(deleted)
        self.assertIsNone(self.client.get("to-delete"))

    def test_delete_nonexistent(self):
        result = self.client.delete("nope")
        self.assertFalse(result)

    def test_format_listing(self):
        self.client.publish("agent-1", _make_payload(), tags=["prod"])
        output = self.client.format_listing()
        self.assertIn("agent-1", output)
        self.assertIn("1 schemas", output)

    def test_format_listing_empty(self):
        output = self.client.format_listing()
        self.assertIn("empty", output.lower())


class TestRegistryEntry(unittest.TestCase):
    """Test RegistryEntry data class."""

    def test_to_dict(self):
        entry = RegistryEntry(
            name="test",
            description="desc",
            framework="langgraph",
            version="1.0",
            tags=["a"],
            author="me",
            published_at="now",
            message_count=5,
            memory_keys=3,
        )
        d = entry.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["message_count"], 5)

    def test_from_dict(self):
        data = {
            "name": "test",
            "description": "desc",
            "framework": "crewai",
            "version": "1.0",
            "tags": ["b"],
            "author": "you",
            "published_at": "now",
            "message_count": 2,
            "memory_keys": 1,
        }
        entry = RegistryEntry.from_dict(data)
        self.assertEqual(entry.framework, "crewai")


if __name__ == "__main__":
    unittest.main()
