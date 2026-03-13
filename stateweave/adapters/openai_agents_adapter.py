"""
OpenAI Agents SDK Adapter — Translates OpenAI agent state ↔ Universal Schema.
================================================================================
Maps OpenAI Agents SDK Sessions (SQLite/Redis/SQLAlchemy), Context, and
conversation history to the StateWeave Universal Schema.

OpenAI Agents SDK stores state as:
  - Sessions (persistent conversation history via SQLite/Redis/SQLAlchemy)
  - Context object (dependency injection container across runs)
  - Tool definitions and results
  - Agent handoff state
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.adapters.base import AdapterTier, ExportError, ImportError_, StateWeaveAdapter
from stateweave.schema.v1 import (
    AccessPolicy,
    AgentInfo,
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

logger = logging.getLogger("stateweave.adapters.openai_agents")

OPENAI_AGENTS_TARGET_VERSION = "0.1.x"

# Role mapping: OpenAI Agents SDK → Universal Schema
OPENAI_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
    "developer": MessageRole.SYSTEM,
}

UNIVERSAL_TO_OPENAI_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

# Internal fields that are non-portable
OPENAI_INTERNAL_KEYS = {
    "_session_backend",
    "_session_id_internal",
    "_api_key",
    "_organization_id",
    "_project_id",
    "_client_ref",
}


class OpenAIAgentsAdapter(StateWeaveAdapter):
    """Adapter for OpenAI Agents SDK (openai-agents>=0.1.0).

    Translates between OpenAI Agents SDK's Sessions + Context and the
    StateWeave Universal Schema.

    Supports:
      - Session-based conversation history (SQLite, Redis, SQLAlchemy)
      - Context objects with injected dependencies
      - Tool definitions and call results
      - Agent handoff chains

    Usage:
        adapter = OpenAIAgentsAdapter(session=my_session)
        payload = adapter.export_state("my-agent")
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        session: Optional[Any] = None,
        context: Optional[Any] = None,
    ):
        """Initialize the OpenAI Agents adapter.

        Args:
            agent: An OpenAI Agents SDK Agent instance.
            session: A session object (SQLiteSession, etc.).
            context: A context object passed to agent runs.
        """
        self._agent = agent
        self._session = session
        self._context = context
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "openai_agents"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_2

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export OpenAI Agents SDK state to Universal Schema.

        Args:
            agent_id: Identifier for this agent.
            **kwargs: Additional options:
                - include_session_history: bool (default True)
                - include_tool_defs: bool (default True)

        Returns:
            StateWeavePayload with the agent's cognitive state.
        """
        include_history = kwargs.get("include_session_history", True)
        include_tools = kwargs.get("include_tool_defs", True)

        try:
            state = self._extract_state(agent_id, include_tools)
        except Exception as e:
            raise ExportError(f"Failed to get OpenAI Agents state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(state, include_history)
        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get(
                "agent_name",
                state.get("agent_name", f"openai-agents-{agent_id}"),
            ),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["openai_agents"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "agent_type": type(self._agent).__name__ if self._agent else "unknown",
                "session_backend": type(self._session).__name__ if self._session else "none",
                "has_context": self._context is not None,
                "has_handoffs": bool(state.get("handoffs")),
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="openai_agents",
                success=True,
                details={
                    "agent_id": agent_id,
                    "state_keys": list(state.keys()),
                    "session_type": type(self._session).__name__ if self._session else "none",
                },
            )
        ]

        return StateWeavePayload(
            source_framework="openai_agents",
            source_version=OPENAI_AGENTS_TARGET_VERSION,
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
        """Import a StateWeavePayload into OpenAI Agents SDK.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - agent_id: str — target agent identifier

        Returns:
            Dict with agent_id and restored state info.
        """
        target_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            # If a session is available, push messages into it
            if self._session and hasattr(self._session, "add_message"):
                for msg in state_dict.get("messages", []):
                    self._session.add_message(msg)

            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into OpenAI Agents '{target_id}' (from {payload.source_framework})"
            )

            return {
                "agent_id": target_id,
                "framework": "openai_agents",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import into OpenAI Agents '{target_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known OpenAI Agents."""
        agents = []

        if self._agent:
            name = getattr(self._agent, "name", "default")
            agents.append(
                AgentInfo(
                    agent_id=name,
                    agent_name=f"openai-agents-{name}",
                    framework="openai_agents",
                    metadata={"source": "live_agent"},
                )
            )

        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"openai-agents-{agent_id}",
                    framework="openai_agents",
                    metadata={"source": "local_store"},
                )
            )

        return agents

    def _extract_state(self, agent_id: str = "", include_tools: bool = True) -> Dict[str, Any]:
        """Extract state from OpenAI Agents SDK components or local store."""
        state: Dict[str, Any] = {}

        # Extract agent metadata
        if self._agent:
            state["agent_name"] = getattr(self._agent, "name", "unknown")
            state["instructions"] = getattr(self._agent, "instructions", "")
            state["model"] = getattr(self._agent, "model", "unknown")

            if include_tools and hasattr(self._agent, "tools"):
                state["tools"] = []
                for tool in self._agent.tools:
                    tool_info: Dict[str, Any] = {}
                    if hasattr(tool, "name"):
                        tool_info["name"] = tool.name
                    elif hasattr(tool, "__name__"):
                        tool_info["name"] = tool.__name__
                    else:
                        tool_info["name"] = type(tool).__name__
                    if hasattr(tool, "description"):
                        tool_info["description"] = tool.description
                    state["tools"].append(tool_info)

            # Extract handoffs
            if hasattr(self._agent, "handoffs"):
                state["handoffs"] = []
                for handoff in self._agent.handoffs:
                    h_info: Dict[str, Any] = {}
                    if hasattr(handoff, "agent"):
                        h_info["target_agent"] = getattr(handoff.agent, "name", str(handoff.agent))
                    if hasattr(handoff, "name"):
                        h_info["name"] = handoff.name
                    state["handoffs"].append(h_info)

        # Extract session history
        if self._session:
            if hasattr(self._session, "get_messages"):
                raw_messages = self._session.get_messages()
                state["session_messages"] = []
                for msg in raw_messages:
                    if isinstance(msg, dict):
                        state["session_messages"].append(msg)
                    elif hasattr(msg, "dict"):
                        state["session_messages"].append(msg.dict())
                    elif hasattr(msg, "model_dump"):
                        state["session_messages"].append(msg.model_dump())

        # Extract context
        if self._context:
            if hasattr(self._context, "__dict__"):
                context_data = {}
                for k, v in self._context.__dict__.items():
                    if not k.startswith("_"):
                        try:
                            # Only serialize simple types
                            if isinstance(v, (str, int, float, bool, list, dict)):
                                context_data[k] = v
                        except Exception:
                            pass
                state["context"] = context_data

        # Fallback: if no live agent/session objects, check _agents store
        if not state and agent_id and agent_id in self._agents:
            state = self._agents[agent_id]

        return state

    def _translate_to_cognitive_state(
        self,
        state: Dict[str, Any],
        include_history: bool = True,
    ) -> CognitiveState:
        """Translate OpenAI Agents state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        goal_tree: Dict[str, GoalNode] = {}
        tool_results: Dict[str, ToolResult] = {}

        # Extract session messages
        if include_history and "session_messages" in state:
            for msg in state["session_messages"]:
                if isinstance(msg, dict):
                    role_str = msg.get("role", "user")
                    role = OPENAI_ROLE_MAP.get(role_str, MessageRole.HUMAN)
                    messages.append(
                        Message(
                            role=role,
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

        # Extract agent instructions into working memory
        if "instructions" in state:
            working_memory["openai_instructions"] = state["instructions"]
        if "model" in state:
            working_memory["openai_model"] = state["model"]
        if "context" in state:
            working_memory["openai_context"] = state["context"]

        # Extract tools
        if "tools" in state:
            for tool in state["tools"]:
                if isinstance(tool, dict):
                    name = tool.get("name", "unknown")
                    tool_results[name] = ToolResult(
                        tool_name=name,
                        arguments={},
                        result={"description": tool.get("description", "")},
                        success=True,
                    )

        # Extract handoffs as goal tree
        if "handoffs" in state:
            for i, handoff in enumerate(state["handoffs"]):
                if isinstance(handoff, dict):
                    goal_id = f"handoff_{i}"
                    goal_tree[goal_id] = GoalNode(
                        goal_id=goal_id,
                        description=(f"Handoff to {handoff.get('target_agent', 'unknown')}"),
                        status="pending",
                        metadata=handoff,
                    )

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            goal_tree=goal_tree,
            tool_results_cache=tool_results,
        )

    def _translate_from_cognitive_state(
        self,
        cognitive_state: CognitiveState,
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to OpenAI Agents state."""
        state: Dict[str, Any] = {}

        # Restore messages
        if cognitive_state.conversation_history:
            state["messages"] = []
            for msg in cognitive_state.conversation_history:
                role = UNIVERSAL_TO_OPENAI_ROLE.get(msg.role, "user")
                msg_dict: Dict[str, Any] = {
                    "role": role,
                    "content": msg.content,
                }
                if msg.name:
                    msg_dict["name"] = msg.name
                if msg.tool_call_id:
                    msg_dict["tool_call_id"] = msg.tool_call_id
                state["messages"].append(msg_dict)

        # Restore agent config from working memory
        if "openai_instructions" in cognitive_state.working_memory:
            state["instructions"] = cognitive_state.working_memory["openai_instructions"]
        if "openai_model" in cognitive_state.working_memory:
            state["model"] = cognitive_state.working_memory["openai_model"]
        if "openai_context" in cognitive_state.working_memory:
            state["context"] = cognitive_state.working_memory["openai_context"]

        return state

    def _detect_non_portable(
        self,
        state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect OpenAI Agents-specific non-portable elements."""
        warnings = []

        # API credentials
        for key in OPENAI_INTERNAL_KEYS:
            if key in state:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"OpenAI internal '{key}' contains credentials/refs",
                        severity=NonPortableWarningSeverity.CRITICAL,
                        data_loss=False,
                        recommendation="Stripped during export. Reconfigure after import.",
                    )
                )

        # Session backend is non-portable
        if self._session:
            warnings.append(
                NonPortableWarning(
                    field="session",
                    reason=(
                        f"Session backend ({type(self._session).__name__}) is "
                        "infrastructure-specific"
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=False,
                    recommendation=(
                        "Session data (messages) is exported. The backend "
                        "connection must be reconfigured after import."
                    ),
                )
            )

        # Handoffs reference specific agents
        if "handoffs" in state:
            warnings.append(
                NonPortableWarning(
                    field="handoffs",
                    reason=(
                        "Handoff definitions reference specific agent instances "
                        "that may not exist in the target framework"
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=False,
                    recommendation=(
                        "Handoffs are preserved as goal tree entries. "
                        "Re-wire agent connections after import."
                    ),
                )
            )

        # Tool callables
        if "tools" in state:
            warnings.append(
                NonPortableWarning(
                    field="tools",
                    reason="Tool metadata only — callables are framework-specific",
                    severity=NonPortableWarningSeverity.INFO,
                    data_loss=False,
                    recommendation="Re-register tools in the target framework",
                )
            )

        return warnings
