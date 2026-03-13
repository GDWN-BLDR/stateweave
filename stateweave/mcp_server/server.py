"""
MCP Server — StateWeave as an MCP Server.
===========================================
Exposes StateWeave's export/import/diff capabilities as MCP Tools,
with schema documentation and migration history as Resources.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.adapters.autogen_adapter import AutoGenAdapter
from stateweave.adapters.crewai_adapter import CrewAIAdapter
from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.diff import diff_payloads
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.validator import get_schema_json, validate_payload

logger = logging.getLogger("stateweave.mcp_server.server")

# Global state for the MCP server
_serializer = StateWeaveSerializer(pretty=True)
_migration_history: List[Dict[str, Any]] = []
_adapters: Dict[str, Any] = {
    "langgraph": LangGraphAdapter(),
    "mcp": MCPAdapter(),
    "crewai": CrewAIAdapter(),
    "autogen": AutoGenAdapter(),
}


# =============================================================
# MCP Tools
# =============================================================


async def export_agent_state(
    framework: str,
    agent_id: str,
    encrypt: bool = False,
) -> Dict[str, Any]:
    """Export an agent's cognitive state from a framework.

    Extracts the agent's full cognitive state (conversation history,
    working memory, goals, tool results) and packages it in the
    Universal Schema format.

    Args:
        framework: Source framework name ("langgraph", "mcp").
        agent_id: Identifier of the agent to export.
        encrypt: Whether to encrypt the exported payload.

    Returns:
        Dict containing the exported StateWeavePayload as JSON,
        along with export metadata and non-portable warnings.
    """
    if framework not in _adapters:
        return {
            "success": False,
            "error": f"Unknown framework: {framework}. Available: {list(_adapters.keys())}",
        }

    adapter = _adapters[framework]
    engine = MigrationEngine(serializer=_serializer)

    result = engine.export_state(
        adapter=adapter,
        agent_id=agent_id,
        encrypt=encrypt,
        analyze_portability=True,
    )

    if result.success and result.payload:
        payload_dict = _serializer.to_dict(result.payload)
        _migration_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "export",
                "framework": framework,
                "agent_id": agent_id,
                "success": True,
            }
        )
        return {
            "success": True,
            "payload": payload_dict,
            "warnings": result.warnings,
            "message": f"Successfully exported agent '{agent_id}' from {framework}",
        }
    else:
        return {
            "success": False,
            "error": result.error,
        }


async def import_agent_state(
    target_framework: str,
    payload: Dict[str, Any],
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Import an agent's cognitive state into a target framework.

    Takes a StateWeavePayload (in Universal Schema format) and
    translates it into the target framework's native representation.

    Args:
        target_framework: Target framework name ("langgraph", "mcp").
        payload: The StateWeavePayload as a JSON dict.
        agent_id: Optional override for the target agent ID.

    Returns:
        Dict with import results including the target agent reference.
    """
    if target_framework not in _adapters:
        return {
            "success": False,
            "error": f"Unknown framework: {target_framework}. Available: {list(_adapters.keys())}",
        }

    # Validate payload
    is_valid, errors = validate_payload(payload)
    if not is_valid:
        return {
            "success": False,
            "error": f"Invalid payload: {errors}",
        }

    adapter = _adapters[target_framework]
    engine = MigrationEngine(serializer=_serializer)

    sw_payload = _serializer.from_dict(payload)
    kwargs = {}
    if agent_id:
        kwargs["agent_id"] = agent_id

    result = engine.import_state(
        adapter=adapter,
        payload=sw_payload,
        **kwargs,
    )

    if result.success:
        _migration_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "import",
                "framework": target_framework,
                "agent_id": agent_id or payload.get("metadata", {}).get("agent_id"),
                "source_framework": payload.get("source_framework"),
                "success": True,
            }
        )
        return {
            "success": True,
            "message": f"Successfully imported into {target_framework}",
            "warnings": result.warnings,
        }
    else:
        return {
            "success": False,
            "error": result.error,
        }


async def diff_agent_states(
    state_a: Dict[str, Any],
    state_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare two agent states and return a detailed diff report.

    Computes the structural differences between two StateWeavePayloads,
    showing what changed in conversation history, working memory,
    goals, and tool results.

    Args:
        state_a: The "before" state as a StateWeavePayload JSON dict.
        state_b: The "after" state as a StateWeavePayload JSON dict.

    Returns:
        Dict with diff report including change counts and details.
    """
    try:
        payload_a = _serializer.from_dict(state_a)
        payload_b = _serializer.from_dict(state_b)
    except Exception as e:
        return {
            "success": False,
            "error": f"Invalid payload(s): {e}",
        }

    diff = diff_payloads(payload_a, payload_b)

    return {
        "success": True,
        "has_changes": diff.has_changes,
        "summary": diff.summary,
        "added": diff.added_count,
        "removed": diff.removed_count,
        "modified": diff.modified_count,
        "report": diff.to_report(),
        "entries": [
            {
                "path": e.path,
                "type": e.diff_type,
                "old": repr(e.old_value)[:200] if e.old_value else None,
                "new": repr(e.new_value)[:200] if e.new_value else None,
            }
            for e in diff.entries[:50]  # Cap at 50 entries
        ],
    }


# =============================================================
# MCP Resources
# =============================================================


def get_schema_resource() -> Dict[str, Any]:
    """Get the current Universal Schema specification.

    Resource URI: stateweave://schemas/v1
    """
    return {
        "uri": "stateweave://schemas/v1",
        "name": "StateWeave Universal Schema v1",
        "description": "The canonical JSON Schema for agent cognitive state",
        "mimeType": "application/json",
        "content": json.dumps(get_schema_json(), indent=2),
    }


def get_migration_history_resource() -> Dict[str, Any]:
    """Get the migration history log.

    Resource URI: stateweave://migrations/history
    """
    return {
        "uri": "stateweave://migrations/history",
        "name": "Migration History",
        "description": "Log of all export/import operations",
        "mimeType": "application/json",
        "content": json.dumps(_migration_history, indent=2),
    }


def get_agent_snapshot_resource(agent_id: str) -> Dict[str, Any]:
    """Get a live state snapshot for a specific agent.

    Resource URI: stateweave://agents/{agent_id}/snapshot
    """
    for framework_name, adapter in _adapters.items():
        agents = adapter.list_agents()
        for agent in agents:
            if agent.agent_id == agent_id:
                try:
                    payload = adapter.export_state(agent_id)
                    return {
                        "uri": f"stateweave://agents/{agent_id}/snapshot",
                        "name": f"Agent Snapshot: {agent_id}",
                        "description": f"Live state snapshot for agent {agent_id}",
                        "mimeType": "application/json",
                        "content": _serializer.dumps(payload).decode("utf-8"),
                    }
                except Exception as e:
                    return {
                        "uri": f"stateweave://agents/{agent_id}/snapshot",
                        "error": str(e),
                    }

    return {
        "uri": f"stateweave://agents/{agent_id}/snapshot",
        "error": f"Agent '{agent_id}' not found",
    }


# =============================================================
# MCP Prompts
# =============================================================

BACKUP_BEFORE_RISKY_OPERATION = {
    "name": "backup_before_risky_operation",
    "description": (
        "Template for agents to self-request a state backup before "
        "performing risky operations (database writes, API calls, etc.)"
    ),
    "arguments": [
        {
            "name": "operation_description",
            "description": "What risky operation is about to be performed",
            "required": True,
        },
        {
            "name": "agent_id",
            "description": "ID of the agent to back up",
            "required": True,
        },
    ],
    "template": (
        "Before performing the following operation, create a state backup:\n\n"
        "Operation: {operation_description}\n"
        "Agent: {agent_id}\n\n"
        "Steps:\n"
        "1. Call export_agent_state to save current state\n"
        "2. Perform the operation\n"
        "3. If the operation fails, use import_agent_state to restore\n"
        "4. If successful, the backup can be used for audit purposes"
    ),
}

MIGRATION_GUIDE = {
    "name": "migration_guide",
    "description": ("Step-by-step guide for migrating an agent between frameworks"),
    "arguments": [
        {
            "name": "source_framework",
            "description": "Framework to migrate from",
            "required": True,
        },
        {
            "name": "target_framework",
            "description": "Framework to migrate to",
            "required": True,
        },
        {
            "name": "agent_id",
            "description": "ID of the agent to migrate",
            "required": True,
        },
    ],
    "template": (
        "# Agent Migration Guide\n\n"
        "Migrating agent '{agent_id}' from {source_framework} to "
        "{target_framework}.\n\n"
        "## Steps:\n"
        "1. **Export**: Call export_agent_state(framework='{source_framework}', "
        "agent_id='{agent_id}')\n"
        "2. **Review Warnings**: Check non_portable_warnings for any data "
        "that cannot transfer\n"
        "3. **Import**: Call import_agent_state(target_framework="
        "'{target_framework}', payload=<exported_payload>)\n"
        "4. **Verify**: Use diff_agent_states to compare before/after\n"
        "5. **Test**: Interact with the migrated agent to verify continuity\n\n"
        "## Important Notes:\n"
        "- Database cursors and live connections will NOT transfer\n"
        "- API keys and credentials are stripped for security\n"
        "- Conversation history and working memory WILL transfer\n"
        "- The agent may need to re-establish tool connections"
    ),
}
