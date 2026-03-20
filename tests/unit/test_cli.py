"""
Unit Tests: CLI
=================
Tests for the StateWeave CLI commands.
"""

import json
import subprocess
import sys

import stateweave
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class TestCLI:
    """Tests for CLI commands via subprocess."""

    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert f"stateweave {stateweave.__version__}" in result.stdout
        assert "Adapters:" in result.stdout

    def test_schema_stdout(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "schema"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        schema = json.loads(result.stdout)
        assert "properties" in schema
        assert "stateweave_version" in schema["properties"]

    def test_schema_to_file(self, tmp_path):
        out = tmp_path / "schema.json"
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "schema", "-o", str(out)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert out.exists()
        schema = json.loads(out.read_text())
        assert "properties" in schema

    def test_validate_valid_payload(self, tmp_path):
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="test-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="hello"),
                ],
            ),
        )
        serializer = StateWeaveSerializer(pretty=True)
        payload_file = tmp_path / "state.json"
        payload_file.write_bytes(serializer.dumps(payload))

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "validate", str(payload_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Valid StateWeavePayload" in result.stdout

    def test_validate_invalid_payload(self, tmp_path):
        payload_file = tmp_path / "bad.json"
        payload_file.write_text('{"invalid": true}')

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "validate", str(payload_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Invalid" in result.stderr or "Error" in result.stderr

    def test_validate_missing_file(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "validate", "/nonexistent.json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_diff_two_files(self, tmp_path):
        serializer = StateWeaveSerializer(pretty=True)

        payload_a = StateWeavePayload(
            source_framework="langgraph",
            metadata=AgentMetadata(agent_id="a"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="hello"),
                ],
            ),
        )
        payload_b = StateWeavePayload(
            source_framework="mcp",
            metadata=AgentMetadata(agent_id="a"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="hello"),
                    Message(role=MessageRole.ASSISTANT, content="hi there"),
                ],
            ),
        )

        file_a = tmp_path / "state_a.json"
        file_b = tmp_path / "state_b.json"
        file_a.write_bytes(serializer.dumps(payload_a))
        file_b.write_bytes(serializer.dumps(payload_b))

        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "diff", str(file_a), str(file_b)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "DIFF REPORT" in result.stdout

    def test_help_shows_examples(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "stateweave quickstart" in result.stdout
        assert "stateweave version" in result.stdout
        assert "stateweave why" in result.stdout

    def test_no_command_shows_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0  # exits with 1


class TestMCPServerImport:
    """Verify MCP server module can be imported."""

    def test_main_importable(self):
        from stateweave.mcp_server import __main__

        assert hasattr(__main__, "main")
        assert hasattr(__main__, "handle_jsonrpc")

    def test_server_importable(self):
        from stateweave.mcp_server import server

        assert hasattr(server, "export_agent_state")
        assert hasattr(server, "import_agent_state")
        assert hasattr(server, "diff_agent_states")

    def test_all_adapters_registered(self):
        from stateweave.mcp_server.server import _adapters

        assert "langgraph" in _adapters
        assert "mcp" in _adapters
        assert "crewai" in _adapters
        assert "autogen" in _adapters
