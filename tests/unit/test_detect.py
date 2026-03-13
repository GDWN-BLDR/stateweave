"""Tests for framework auto-detection."""

import json
import tempfile

from stateweave.core.detect import detect_framework


class TestDetectFramework:
    """Test suite for framework auto-detection."""

    def test_detect_dspy_state(self):
        state = {"signature": {"input": "q"}, "demos": [{"q": "test"}], "lm": {}}
        results = detect_framework(state)
        assert results[0][0] == "dspy"
        assert results[0][1] >= 0.5

    def test_detect_langgraph_state(self):
        state = {
            "checkpoint_id": "abc",
            "channel_values": {"messages": []},
            "__channel_versions__": {},
        }
        results = detect_framework(state)
        assert results[0][0] == "langgraph"
        assert results[0][1] >= 0.7

    def test_detect_letta_state(self):
        state = {
            "core_memory": {"persona": "test"},
            "archival_memory": [],
            "recall_memory": [],
        }
        results = detect_framework(state)
        assert results[0][0] == "letta"
        assert results[0][1] >= 0.7

    def test_detect_openai_agents_state(self):
        state = {
            "session_messages": [{"role": "user", "content": "hi"}],
            "handoffs": [],
        }
        results = detect_framework(state)
        assert results[0][0] == "openai_agents"

    def test_detect_semantic_kernel_state(self):
        state = {"thread_state": {}, "plugins": [{"name": "test"}]}
        results = detect_framework(state)
        assert results[0][0] == "semantic_kernel"

    def test_detect_from_json_string(self):
        state_json = json.dumps({"signature": {}, "demos": []})
        results = detect_framework(state_json)
        assert results[0][0] == "dspy"

    def test_detect_from_file(self):
        state = {"core_memory": {"persona": "test"}, "archival_memory": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(state, f)
            f.flush()
            results = detect_framework(f.name)
        assert results[0][0] == "letta"

    def test_detect_empty_state(self):
        results = detect_framework({})
        assert results[0] == ("unknown", 0.0)

    def test_detect_top_n(self):
        state = {"messages": [], "tools": []}  # Ambiguous
        results = detect_framework(state, top_n=3)
        assert len(results) <= 3

    def test_detect_haystack_state(self):
        state = {"long_term_memories": [], "_pipeline_ref": "test"}
        results = detect_framework(state)
        assert results[0][0] == "haystack"

    def test_detect_crewai_state(self):
        state = {"crew_output": {}, "agents": [], "tasks": []}
        results = detect_framework(state)
        assert results[0][0] == "crewai"
