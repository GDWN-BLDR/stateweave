"""
MCP Adapter — Translates MCP client state ↔ Universal Schema.
================================================================
Since MCP is inherently stateless at the protocol level, this adapter
aggregates state from MCP client interactions (conversation context,
tool call history, resource reads) into the Universal Schema.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from stateweave.adapters.base import AdapterTier, ExportError, ImportError_, StateWeaveAdapter
from stateweave.schema.v1 import (
    AccessPolicy,
    AgentInfo,
    AgentMetadata,
    AuditAction,
    AuditEntry,
    CognitiveState,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)

# Conditional imports: use native MCP SDK types when available
try:
    from mcp.types import Resource as MCPResource  # noqa: F401
    from mcp.types import Tool as MCPTool  # noqa: F401

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

logger = logging.getLogger("stateweave.adapters.mcp")

MCP_TARGET_VERSION = "1.0.x"


class MCPAdapter(StateWeaveAdapter):
    """Adapter for MCP (Model Context Protocol) agents.

    Since MCP is stateless at the protocol level, this adapter works
    by aggregating state from MCP client-side tracking:
    - Conversation messages
    - Tool call history and results
    - Resource read cache
    - Server connection metadata

    Usage:
        adapter = MCPAdapter()
        # Register an agent's state manually
        adapter.register_agent("my-agent", {
            "messages": [...],
            "tool_calls": [...],
            "resources": {...},
        })
        payload = adapter.export_state("my-agent")
    """

    def __init__(self):
        """Initialize the MCP adapter."""
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "mcp"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_1

    def register_agent(
        self,
        agent_id: str,
        state: Dict[str, Any],
    ) -> None:
        """Register an MCP agent's accumulated state.

        Since MCP is stateless, the client must track state and provide
        it to this adapter for export.

        Args:
            agent_id: Identifier for the agent.
            state: Dict containing accumulated state:
                - messages: List[Dict] — conversation history
                - tool_calls: List[Dict] — tool invocation history
                - resources: Dict — cached resource reads
                - servers: List[str] — connected MCP server URIs
                - prompts: Dict — active prompt state
        """
        self._agents[agent_id] = {
            **state,
            "_registered_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Registered MCP agent state: {agent_id}")

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export MCP agent state to Universal Schema.

        Args:
            agent_id: The agent identifier.

        Returns:
            StateWeavePayload with aggregated MCP state.
        """
        if agent_id not in self._agents:
            raise ExportError(
                f"MCP agent '{agent_id}' not registered. Call register_agent() first."
            )

        raw_state = self._agents[agent_id]

        # Translate to cognitive state
        cognitive_state = self._translate_to_cognitive_state(raw_state)

        # Detect non-portable elements
        warnings = self._detect_non_portable(raw_state)

        # Build metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"mcp-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["mcp"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "servers": raw_state.get("servers", []),
                "protocol_version": MCP_TARGET_VERSION,
            },
        )

        # Build audit trail
        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="mcp",
                success=True,
                details={
                    "agent_id": agent_id,
                    "message_count": len(raw_state.get("messages", [])),
                    "tool_call_count": len(raw_state.get("tool_calls", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="mcp",
            source_version=MCP_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(
        self,
        payload: StateWeavePayload,
        **kwargs,
    ) -> Any:
        """Import a StateWeavePayload into an MCP context.

        Translates Universal Schema back to MCP-compatible state
        and registers it locally.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - agent_id: str — override agent ID

        Returns:
            Dict with agent_id and state summary.
        """
        agent_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            # Preserve source framework info
            state_dict["_imported_from"] = payload.source_framework
            state_dict["_import_timestamp"] = datetime.utcnow().isoformat()

            self._agents[agent_id] = state_dict

            logger.info(
                f"Imported state into MCP agent '{agent_id}' (from {payload.source_framework})"
            )

            return {
                "agent_id": agent_id,
                "framework": "mcp",
                "message_count": len(state_dict.get("messages", [])),
                "resource_count": len(state_dict.get("resources", {})),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import state into MCP agent '{agent_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all registered MCP agents."""
        agents = []
        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"mcp-{agent_id}",
                    framework="mcp",
                    last_active=datetime.fromisoformat(state["_registered_at"])
                    if "_registered_at" in state
                    else None,
                    metadata={
                        "message_count": len(state.get("messages", [])),
                        "servers": state.get("servers", []),
                    },
                )
            )
        return agents

    def _translate_to_cognitive_state(
        self,
        raw_state: Dict[str, Any],
    ) -> CognitiveState:
        """Translate MCP accumulated state to Universal Schema CognitiveState."""
        messages = []
        tool_results = {}
        working_memory = {}

        # Translate messages
        for msg in raw_state.get("messages", []):
            role_str = msg.get("role", "user")
            role_map = {
                "user": MessageRole.HUMAN,
                "assistant": MessageRole.ASSISTANT,
                "system": MessageRole.SYSTEM,
                "tool": MessageRole.TOOL,
            }
            messages.append(
                Message(
                    role=role_map.get(role_str, MessageRole.HUMAN),
                    content=str(msg.get("content", "")),
                    name=msg.get("name"),
                    tool_call_id=msg.get("tool_call_id"),
                    metadata={
                        k: v
                        for k, v in msg.items()
                        if k not in ("role", "content", "name", "tool_call_id")
                    },
                )
            )

        # Translate tool calls
        for tool_call in raw_state.get("tool_calls", []):
            tool_name = tool_call.get("name", tool_call.get("tool", "unknown"))
            tool_results[tool_name] = ToolResult(
                tool_name=tool_name,
                arguments=tool_call.get("arguments", {}),
                result=tool_call.get("result"),
                success=tool_call.get("success", True),
                error=tool_call.get("error"),
            )

        # Resources go to working memory
        if "resources" in raw_state:
            working_memory["resources"] = raw_state["resources"]

        # Prompt state
        if "prompts" in raw_state:
            working_memory["active_prompts"] = raw_state["prompts"]

        # Server info
        if "servers" in raw_state:
            working_memory["connected_servers"] = raw_state["servers"]

        # Any other custom state
        skip_keys = {
            "messages",
            "tool_calls",
            "resources",
            "prompts",
            "servers",
            "_registered_at",
            "_imported_from",
            "_import_timestamp",
        }
        for key, value in raw_state.items():
            if key not in skip_keys:
                working_memory[key] = value

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            tool_results_cache=tool_results,
        )

    def _translate_from_cognitive_state(
        self,
        cognitive_state: CognitiveState,
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to MCP state dict."""
        state: Dict[str, Any] = {}

        # Convert messages
        if cognitive_state.conversation_history:
            messages = []
            role_map = {
                MessageRole.HUMAN: "user",
                MessageRole.ASSISTANT: "assistant",
                MessageRole.SYSTEM: "system",
                MessageRole.TOOL: "tool",
                MessageRole.FUNCTION: "tool",
            }
            for msg in cognitive_state.conversation_history:
                messages.append(
                    {
                        "role": role_map.get(msg.role, "user"),
                        "content": msg.content,
                        **({"name": msg.name} if msg.name else {}),
                        **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                    }
                )
            state["messages"] = messages

        # Convert tool results to tool_calls
        if cognitive_state.tool_results_cache:
            tool_calls = []
            for key, tool_result in cognitive_state.tool_results_cache.items():
                if isinstance(tool_result, ToolResult):
                    tool_calls.append(
                        {
                            "name": tool_result.tool_name,
                            "arguments": tool_result.arguments,
                            "result": tool_result.result,
                            "success": tool_result.success,
                        }
                    )
            state["tool_calls"] = tool_calls

        # Extract resources from working memory
        wm = cognitive_state.working_memory
        if "resources" in wm:
            state["resources"] = wm.pop("resources")
        if "active_prompts" in wm:
            state["prompts"] = wm.pop("active_prompts")
        if "connected_servers" in wm:
            state["servers"] = wm.pop("connected_servers")

        # Remaining working memory
        state.update(wm)

        return state

    def _detect_non_portable(
        self,
        raw_state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect MCP-specific non-portable elements."""
        warnings = []

        # OAuth tokens should never transfer
        for key in raw_state:
            if "oauth" in key.lower() or "token" in key.lower():
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason="Security-sensitive credentials must not transfer",
                        severity=NonPortableWarningSeverity.CRITICAL,
                        data_loss=True,
                        recommendation="Use environment variables for credentials",
                    )
                )

        # Server connections are non-portable
        if "servers" in raw_state:
            warnings.append(
                NonPortableWarning(
                    field="state.servers",
                    reason="MCP server connection URIs are environment-specific",
                    severity=NonPortableWarningSeverity.INFO,
                    data_loss=False,
                    recommendation="Re-establish server connections after import",
                )
            )

        return warnings
