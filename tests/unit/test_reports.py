"""Tests for shareable migration reports."""

import json

from stateweave.core.reports import MigrationReport
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
)


def _make_payload(framework="langgraph", agent_id="test", messages=None, warnings=None):
    return StateWeavePayload(
        source_framework=framework,
        metadata=AgentMetadata(agent_id=agent_id),
        cognitive_state=CognitiveState(
            conversation_history=messages or [],
            working_memory={"key1": "value1"},
        ),
        non_portable_warnings=warnings or [],
    )


class TestMigrationReport:
    """Test suite for MigrationReport."""

    def test_fidelity_score_full(self):
        source = _make_payload(
            messages=[
                Message(role=MessageRole.HUMAN, content="Hello"),
            ]
        )
        target = _make_payload(
            framework="dspy",
            messages=[Message(role=MessageRole.HUMAN, content="Hello")],
        )
        report = MigrationReport(source, target)
        assert report.fidelity_score >= 0.9

    def test_fidelity_score_with_warnings(self):
        source = _make_payload(
            warnings=[
                NonPortableWarning(
                    field="test",
                    reason="test",
                    severity=NonPortableWarningSeverity.CRITICAL,
                ),
            ]
        )
        report = MigrationReport(source)
        assert report.fidelity_score < 1.0

    def test_to_json(self):
        source = _make_payload()
        report = MigrationReport(source)
        json_str = report.to_json()
        data = json.loads(json_str)
        assert "stateweave_migration_report" in data
        assert data["stateweave_migration_report"]["source"]["framework"] == "langgraph"

    def test_to_markdown(self):
        source = _make_payload(
            messages=[
                Message(role=MessageRole.HUMAN, content="Hello"),
            ]
        )
        report = MigrationReport(source)
        md = report.to_markdown()
        assert "# StateWeave Migration Report" in md
        assert "langgraph" in md
        assert "Fidelity Score" in md

    def test_to_html(self):
        source = _make_payload()
        report = MigrationReport(source)
        html = report.to_html()
        assert "<!DOCTYPE html>" in html
        assert "StateWeave" in html
        assert "stateweave.pantollventures.com" in html

    def test_markdown_warnings_table(self):
        source = _make_payload(
            warnings=[
                NonPortableWarning(
                    field="api_key",
                    reason="Contains API credentials",
                    severity=NonPortableWarningSeverity.CRITICAL,
                    data_loss=True,
                ),
            ]
        )
        report = MigrationReport(source)
        md = report.to_markdown()
        assert "api_key" in md
        assert "CRITICAL" in md

    def test_html_warnings_table(self):
        source = _make_payload(
            warnings=[
                NonPortableWarning(
                    field="test_field",
                    reason="Test reason",
                    severity=NonPortableWarningSeverity.WARN,
                ),
            ]
        )
        report = MigrationReport(source)
        html = report.to_html()
        assert "test_field" in html

    def test_fidelity_score_empty_state(self):
        source = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="empty"),
        )
        report = MigrationReport(source)
        assert report.fidelity_score == 1.0
