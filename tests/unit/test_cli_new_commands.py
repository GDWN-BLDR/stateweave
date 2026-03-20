"""
Unit Tests: CLI why and quickstart commands
=============================================
Tests for the stateweave why and stateweave quickstart CLI commands.
"""

import subprocess
import sys

from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import Message


class TestCLIWhy:
    """Tests for the 'stateweave why' CLI command."""

    def test_why_no_checkpoints(self, tmp_path):
        """Should handle agent with no checkpoints gracefully."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "why",
                "nonexistent-agent",
                "--store-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert "Autopsy" in result.stdout or "No checkpoint" in result.stdout

    def test_why_single_checkpoint(self, tmp_path):
        """Should show info but note nothing to compare."""
        from stateweave import LangGraphAdapter

        adapter = LangGraphAdapter()
        payload = adapter.create_sample_payload("why-agent", num_messages=3)

        store = CheckpointStore(store_dir=str(tmp_path))
        store.checkpoint(payload, agent_id="why-agent", label="initial")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "why",
                "why-agent",
                "--store-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "1 checkpoint" in result.stdout or "Only 1" in result.stdout

    def test_why_multiple_checkpoints(self, tmp_path):
        """Should show state evolution and analysis."""
        from stateweave import LangGraphAdapter

        adapter = LangGraphAdapter()
        payload = adapter.create_sample_payload("why-agent", num_messages=2)

        store = CheckpointStore(store_dir=str(tmp_path))
        store.checkpoint(payload, agent_id="why-agent", label="v1")

        # Modify and checkpoint again
        payload.cognitive_state.conversation_history.append(
            Message(role="human", content="Show me the results")
        )
        payload.cognitive_state.working_memory["new_data"] = True
        store.checkpoint(payload, agent_id="why-agent", label="v2")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "why",
                "why-agent",
                "--store-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "v1" in result.stdout
        assert "v2" in result.stdout

    def test_why_verbose_flag(self, tmp_path):
        """Verbose flag should show detailed diff entries."""
        from stateweave import LangGraphAdapter

        adapter = LangGraphAdapter()
        payload = adapter.create_sample_payload("why-agent", num_messages=2)

        store = CheckpointStore(store_dir=str(tmp_path))
        store.checkpoint(payload, agent_id="why-agent", label="v1")
        payload.cognitive_state.working_memory["debug"] = "test"
        store.checkpoint(payload, agent_id="why-agent", label="v2")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "why",
                "why-agent",
                "--store-dir",
                str(tmp_path),
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Verbose should show more detail
        assert len(result.stdout) > 100


class TestCLIQuickstart:
    """Tests for the 'stateweave quickstart' CLI command."""

    def test_quickstart_default(self):
        """Default quickstart should complete successfully."""
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "quickstart"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Quickstart" in result.stdout
        assert "Step 1" in result.stdout
        assert "Step 6" in result.stdout
        assert "Quickstart complete" in result.stdout

    def test_quickstart_with_framework(self):
        """Quickstart should work with --framework flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "quickstart",
                "--framework",
                "mcp",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "mcp" in result.stdout
        assert "Quickstart complete" in result.stdout

    def test_quickstart_invalid_framework(self):
        """Invalid framework should fail cleanly."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "stateweave.cli",
                "quickstart",
                "--framework",
                "nonexistent",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_quickstart_shows_diff(self):
        """Quickstart output should include diff results."""
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "quickstart"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Diff" in result.stdout
        assert "Changes:" in result.stdout

    def test_quickstart_shows_rollback(self):
        """Quickstart output should include rollback results."""
        result = subprocess.run(
            [sys.executable, "-m", "stateweave.cli", "quickstart"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Rollback" in result.stdout
        assert "Restored" in result.stdout
