"""
LangGraph Adapter — Translates LangGraph StateSnapshot ↔ Universal Schema.
============================================================================
Intercepts LangGraph's SerializerProtocol (JsonPlusSerializer) to extract
and inject cognitive state via the StateWeave Universal Schema.
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
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)

# Conditional imports: use native LangGraph types when available
try:
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
    from langgraph.checkpoint.memory import MemorySaver  # noqa: F401
    from langgraph.graph import StateGraph  # noqa: F401

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

logger = logging.getLogger("stateweave.adapters.langgraph")

# LangGraph version this adapter targets
LANGGRAPH_TARGET_VERSION = "1.0.x"

# Message role mapping: LangGraph type names -> Universal Schema roles
LANGGRAPH_ROLE_MAP: Dict[str, MessageRole] = {
    "human": MessageRole.HUMAN,
    "HumanMessage": MessageRole.HUMAN,
    "ai": MessageRole.ASSISTANT,
    "AIMessage": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "SystemMessage": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "ToolMessage": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
    "FunctionMessage": MessageRole.FUNCTION,
}

# Reverse mapping for import
UNIVERSAL_TO_LANGGRAPH_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "human",
    MessageRole.ASSISTANT: "ai",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

# Fields that are LangGraph-internal and should not be exported
LANGGRAPH_INTERNAL_FIELDS = {
    "__channel_versions__",
    "__channel_values__",
    "checkpoint_id",
    "checkpoint_ns",
    "pending_writes",
    "parent_checkpoint_id",
}


class LangGraphAdapter(StateWeaveAdapter):
    """Adapter for LangGraph (langgraph>=0.2.0).

    Translates between LangGraph's internal state representation
    (StateSnapshot / channel values) and the StateWeave Universal Schema.

    This adapter works with LangGraph's checkpointer system, intercepting
    state via the SerializerProtocol interface (dumps_typed / loads_typed).

    Usage:
        adapter = LangGraphAdapter(checkpointer=my_checkpointer)
        payload = adapter.export_state("my-thread-id")
    """

    def __init__(
        self,
        checkpointer: Optional[Any] = None,
        graph: Optional[Any] = None,
    ):
        """Initialize the LangGraph adapter.

        Args:
            checkpointer: LangGraph checkpointer instance (InMemorySaver, etc.).
            graph: Compiled LangGraph graph instance (for get_state/update_state).
        """
        self._checkpointer = checkpointer
        self._graph = graph
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "langgraph"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_1

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export LangGraph agent state to Universal Schema.

        The agent_id corresponds to the LangGraph thread_id.

        Args:
            agent_id: The LangGraph thread_id.
            **kwargs: Additional options:
                - include_history: bool (default True) — include message history
                - config: dict — LangGraph RunnableConfig overrides

        Returns:
            StateWeavePayload with the agent's cognitive state.
        """
        include_history = kwargs.get("include_history", True)
        config = kwargs.get("config", {"configurable": {"thread_id": agent_id}})

        try:
            state_snapshot = self._get_state(agent_id, config)
        except Exception as e:
            raise ExportError(f"Failed to get LangGraph state for thread '{agent_id}': {e}") from e

        # Extract cognitive state from snapshot
        cognitive_state = self._translate_to_cognitive_state(state_snapshot, include_history)

        # Detect non-portable elements
        warnings = self._detect_non_portable(state_snapshot)

        # Build metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"langgraph-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["langgraph"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "checkpointer_type": type(self._checkpointer).__name__
                if self._checkpointer
                else "unknown",
                "has_graph": self._graph is not None,
            },
        )

        # Build audit trail
        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="langgraph",
                success=True,
                details={
                    "thread_id": agent_id,
                    "state_keys": list(state_snapshot.keys())
                    if isinstance(state_snapshot, dict)
                    else [],
                },
            )
        ]

        return StateWeavePayload(
            source_framework="langgraph",
            source_version=LANGGRAPH_TARGET_VERSION,
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
        """Import a StateWeavePayload into LangGraph.

        Creates or updates a LangGraph thread with the imported state.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - thread_id: str — target thread ID (default: payload.metadata.agent_id)

        Returns:
            Dict with thread_id and updated state info.
        """
        thread_id = kwargs.get("thread_id", payload.metadata.agent_id)
        config = {"configurable": {"thread_id": thread_id}}

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            if self._graph:
                self._graph.update_state(config, state_dict)
            else:
                # Store locally if no graph available
                self._agents[thread_id] = state_dict

            logger.info(
                f"Imported state into LangGraph thread '{thread_id}' "
                f"(from {payload.source_framework})"
            )

            return {
                "thread_id": thread_id,
                "framework": "langgraph",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(
                f"Failed to import state into LangGraph thread '{thread_id}': {e}"
            ) from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known LangGraph agents/threads."""
        agents = []

        # From local storage
        for thread_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=thread_id,
                    agent_name=f"langgraph-{thread_id}",
                    framework="langgraph",
                    metadata={"source": "local_store"},
                )
            )

        return agents

    def _get_state(self, agent_id: str, config: Dict) -> Dict[str, Any]:
        """Get state from LangGraph checkpointer or graph."""
        if self._graph:
            snapshot = self._graph.get_state(config)
            return snapshot.values if hasattr(snapshot, "values") else {}
        elif self._checkpointer:
            # Direct checkpointer access
            checkpoint = self._checkpointer.get(config)
            if checkpoint:
                return checkpoint.get("channel_values", {})
            return {}
        elif agent_id in self._agents:
            return self._agents[agent_id]
        else:
            return {}

    def _translate_to_cognitive_state(
        self,
        state: Dict[str, Any],
        include_history: bool = True,
    ) -> CognitiveState:
        """Translate LangGraph state dict to Universal Schema CognitiveState."""
        messages = []
        working_memory = {}
        tool_results = {}

        framework_specific = {}

        for key, value in state.items():
            if key in LANGGRAPH_INTERNAL_FIELDS:
                # Preserve in framework_specific for zero-loss round-trips
                framework_specific[key] = value
                continue

            # Detect message lists
            if key == "messages" and isinstance(value, list) and include_history:
                for msg in value:
                    translated = self._translate_message(msg)
                    if translated:
                        messages.append(translated)
            elif key.endswith("_results") or key.endswith("_cache"):
                # Tool results
                if isinstance(value, dict):
                    for tool_key, tool_val in value.items():
                        tool_results[tool_key] = ToolResult(
                            tool_name=tool_key,
                            result=tool_val,
                            success=True,
                        )
            else:
                # Everything else goes to working memory
                working_memory[key] = value

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            tool_results_cache=tool_results,
            framework_specific=framework_specific,
        )

    def _translate_message(self, msg: Any) -> Optional[Message]:
        """Translate a single LangGraph message to Universal Schema.

        Supports both dict-based messages and native LangChain message
        objects (HumanMessage, AIMessage, etc.) when langgraph is installed.
        """
        # Native LangChain message objects (when langgraph is installed)
        if HAS_LANGGRAPH and isinstance(msg, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
            type_name = type(msg).__name__
            role = LANGGRAPH_ROLE_MAP.get(type_name, MessageRole.HUMAN)
            return Message(
                role=role,
                content=str(msg.content),
                name=getattr(msg, "name", None),
                tool_call_id=getattr(msg, "tool_call_id", None),
            )
        elif isinstance(msg, dict):
            role_str = msg.get("type", msg.get("role", "human"))
            role = LANGGRAPH_ROLE_MAP.get(role_str, MessageRole.HUMAN)
            return Message(
                role=role,
                content=str(msg.get("content", "")),
                name=msg.get("name"),
                tool_call_id=msg.get("tool_call_id"),
                metadata={
                    k: v
                    for k, v in msg.items()
                    if k not in ("type", "role", "content", "name", "tool_call_id")
                },
            )
        elif hasattr(msg, "content"):
            # Generic message-like object
            type_name = type(msg).__name__
            role = LANGGRAPH_ROLE_MAP.get(type_name, MessageRole.HUMAN)
            return Message(
                role=role,
                content=str(msg.content),
                name=getattr(msg, "name", None),
                tool_call_id=getattr(msg, "tool_call_id", None),
            )
        return None

    def _translate_from_cognitive_state(
        self,
        cognitive_state: CognitiveState,
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to LangGraph state dict."""
        state = {}

        # Convert messages
        if cognitive_state.conversation_history:
            messages = []
            for msg in cognitive_state.conversation_history:
                lg_role = UNIVERSAL_TO_LANGGRAPH_ROLE.get(msg.role, "human")
                messages.append(
                    {
                        "type": lg_role,
                        "content": msg.content,
                        **({"name": msg.name} if msg.name else {}),
                        **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                    }
                )
            state["messages"] = messages

        # Restore working memory
        state.update(cognitive_state.working_memory)

        # Restore tool results
        if cognitive_state.tool_results_cache:
            for key, tool_result in cognitive_state.tool_results_cache.items():
                state[f"{key}_results"] = (
                    tool_result.result if isinstance(tool_result, ToolResult) else tool_result
                )

        # Restore framework-specific LangGraph state for zero-loss round-trips
        if cognitive_state.framework_specific:
            for key, value in cognitive_state.framework_specific.items():
                if key in LANGGRAPH_INTERNAL_FIELDS:
                    state[key] = value

        return state

    def _detect_non_portable(
        self,
        state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect LangGraph-specific non-portable elements."""
        warnings = []

        for key in state:
            if key in LANGGRAPH_INTERNAL_FIELDS:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"LangGraph internal field '{key}' is framework-specific",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=False,
                        recommendation="This field will be stripped during export",
                    )
                )

        return warnings
