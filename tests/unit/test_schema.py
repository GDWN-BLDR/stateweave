"""
Unit Tests: Universal Schema v1
=================================
Tests for Pydantic model validation, versioning, edge cases.
"""

import pytest

from stateweave.schema.v1 import (
    SCHEMA_VERSION,
    AgentMetadata,
    AuditAction,
    AuditEntry,
    CognitiveState,
    GoalNode,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)
from stateweave.schema.validator import (
    SchemaValidationError,
    get_schema_json,
    validate_payload,
    validate_payload_strict,
    validate_version_compatibility,
)
from stateweave.schema.versions import (
    get_current_version,
    get_supported_versions,
    is_version_supported,
)


class TestMessage:
    def test_create_human_message(self):
        msg = Message(role=MessageRole.HUMAN, content="Hello, world!")
        assert msg.role == MessageRole.HUMAN
        assert msg.content == "Hello, world!"

    def test_create_tool_message(self):
        msg = Message(
            role=MessageRole.TOOL,
            content="Tool result",
            tool_call_id="tc_123",
            name="search",
        )
        assert msg.role == MessageRole.TOOL
        assert msg.tool_call_id == "tc_123"
        assert msg.name == "search"

    def test_message_with_metadata(self):
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata={"model": "gpt-4", "tokens": 150},
        )
        assert msg.metadata["model"] == "gpt-4"


class TestCognitiveState:
    def test_empty_cognitive_state(self):
        cs = CognitiveState()
        assert cs.conversation_history == []
        assert cs.working_memory == {}
        assert cs.goal_tree == {}
        assert cs.tool_results_cache == {}
        assert cs.trust_parameters == {}

    def test_cognitive_state_with_data(self):
        cs = CognitiveState(
            conversation_history=[
                Message(role=MessageRole.HUMAN, content="Hi"),
                Message(role=MessageRole.ASSISTANT, content="Hello!"),
            ],
            working_memory={"current_task": "research"},
            trust_parameters={"user_trust": 0.9},
        )
        assert len(cs.conversation_history) == 2
        assert cs.working_memory["current_task"] == "research"
        assert cs.trust_parameters["user_trust"] == 0.9


class TestGoalNode:
    def test_create_goal(self):
        goal = GoalNode(
            goal_id="g1",
            description="Complete migration",
            status="active",
        )
        assert goal.goal_id == "g1"
        assert goal.status == "active"
        assert goal.children == []


class TestToolResult:
    def test_create_tool_result(self):
        result = ToolResult(
            tool_name="web_search",
            arguments={"query": "StateWeave"},
            result={"url": "https://example.com"},
            success=True,
        )
        assert result.tool_name == "web_search"
        assert result.success is True

    def test_failed_tool_result(self):
        result = ToolResult(
            tool_name="api_call",
            arguments={},
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestStateWeavePayload:
    def _make_payload(self, **overrides):
        defaults = {
            "source_framework": "langgraph",
            "metadata": AgentMetadata(agent_id="test-agent"),
        }
        defaults.update(overrides)
        return StateWeavePayload(**defaults)

    def test_minimal_valid_payload(self):
        payload = self._make_payload()
        assert payload.stateweave_version == SCHEMA_VERSION
        assert payload.source_framework == "langgraph"
        assert payload.metadata.agent_id == "test-agent"

    def test_full_payload(self):
        payload = self._make_payload(
            source_version="1.0.0",
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                ],
                working_memory={"state": "active"},
            ),
            audit_trail=[
                AuditEntry(
                    action=AuditAction.EXPORT,
                    framework="langgraph",
                    success=True,
                ),
            ],
            non_portable_warnings=[
                NonPortableWarning(
                    field="state.cursor",
                    reason="DB cursor",
                    severity=NonPortableWarningSeverity.WARN,
                ),
            ],
        )
        assert len(payload.cognitive_state.conversation_history) == 1
        assert len(payload.audit_trail) == 1
        assert len(payload.non_portable_warnings) == 1

    def test_invalid_version_format(self):
        with pytest.raises(Exception):
            self._make_payload(stateweave_version="invalid")

    def test_version_must_be_semver(self):
        with pytest.raises(Exception):
            self._make_payload(stateweave_version="1.0")

    def test_payload_serialization_roundtrip(self):
        payload = self._make_payload()
        json_data = payload.model_dump_json()
        restored = StateWeavePayload.model_validate_json(json_data)
        assert restored.source_framework == payload.source_framework
        assert restored.metadata.agent_id == payload.metadata.agent_id


class TestSchemaValidator:
    def test_validate_valid_payload(self):
        data = {
            "source_framework": "langgraph",
            "metadata": {"agent_id": "test"},
        }
        is_valid, errors = validate_payload(data)
        assert is_valid is True
        assert errors == []

    def test_validate_invalid_payload(self):
        data = {}  # Missing required fields
        is_valid, errors = validate_payload(data)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_strict_valid(self):
        data = {
            "source_framework": "mcp",
            "metadata": {"agent_id": "test"},
        }
        payload = validate_payload_strict(data)
        assert payload.source_framework == "mcp"

    def test_validate_strict_invalid(self):
        with pytest.raises(SchemaValidationError):
            validate_payload_strict({})

    def test_version_compatibility(self):
        assert validate_version_compatibility(SCHEMA_VERSION) is True
        assert validate_version_compatibility("0.2.0") is True  # Same major
        assert validate_version_compatibility("1.0.0") is False  # Different major

    def test_get_schema_json(self):
        schema = get_schema_json()
        assert isinstance(schema, dict)
        assert "properties" in schema


class TestSchemaVersions:
    def test_supported_versions(self):
        versions = get_supported_versions()
        assert SCHEMA_VERSION in versions

    def test_current_version(self):
        assert get_current_version() == SCHEMA_VERSION

    def test_version_supported(self):
        assert is_version_supported(SCHEMA_VERSION) is True
        assert is_version_supported("99.0.0") is False
