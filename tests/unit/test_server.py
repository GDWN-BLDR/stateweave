"""
Unit Tests: MCP Server
========================
Tests for MCP server tools and resources.
"""

import asyncio

from stateweave.mcp_server.server import (
    export_agent_state,
    get_agent_snapshot_resource,
    get_migration_history_resource,
    get_schema_resource,
)


class TestMCPServerTools:
    def test_export_unknown_framework(self):
        result = asyncio.get_event_loop().run_until_complete(
            export_agent_state("unknown_fw", "agent1")
        )
        assert result["success"] is False

    def test_schema_resource(self):
        resource = get_schema_resource()
        assert resource["uri"] == "stateweave://schemas/v1"
        assert "content" in resource

    def test_migration_history_resource(self):
        resource = get_migration_history_resource()
        assert resource["uri"] == "stateweave://migrations/history"

    def test_agent_snapshot_not_found(self):
        resource = get_agent_snapshot_resource("nonexistent")
        assert "error" in resource
