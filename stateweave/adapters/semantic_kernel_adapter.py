"""
Semantic Kernel Adapter — Translates SK agent state ↔ Universal Schema.
=========================================================================
Maps Microsoft Semantic Kernel's AgentThread serialization, chat history,
function call results, and plugin metadata to the Universal Schema.

Semantic Kernel stores state as:
  - AgentThread.Serialize() → JSON (conversation history + metadata)
  - ChatHistory (list of ChatMessageContent)
  - Function/Plugin results and invocation metadata
  - Kernel arguments and configuration
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

logger = logging.getLogger("stateweave.adapters.semantic_kernel")

SK_TARGET_VERSION = "1.x"

SK_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "author": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
}

UNIVERSAL_TO_SK_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

SK_INTERNAL_KEYS = {
    "_kernel_ref",
    "_service_id",
    "_ai_connector_ref",
    "_plugin_registry",
    "_api_key",
}


class SemanticKernelAdapter(StateWeaveAdapter):
    """Adapter for Microsoft Semantic Kernel (semantic-kernel>=1.0.0).

    Translates between SK's AgentThread serialization, ChatHistory,
    and plugin system and the StateWeave Universal Schema.

    Usage:
        adapter = SemanticKernelAdapter(thread=my_thread)
        payload = adapter.export_state("my-agent")
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        thread: Optional[Any] = None,
        chat_history: Optional[Any] = None,
        kernel: Optional[Any] = None,
    ):
        """Initialize the Semantic Kernel adapter.

        Args:
            agent: A Semantic Kernel agent instance.
            thread: An AgentThread instance.
            chat_history: A ChatHistory instance.
            kernel: A Kernel instance.
        """
        self._agent = agent
        self._thread = thread
        self._chat_history = chat_history
        self._kernel = kernel
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "semantic_kernel"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.COMMUNITY

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        """Export Semantic Kernel agent state to Universal Schema."""
        try:
            state = self._extract_state()
        except Exception as e:
            raise ExportError(f"Failed to get SK state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(state)
        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"sk-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["semantic_kernel", "microsoft"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "agent_type": type(self._agent).__name__ if self._agent else "unknown",
                "has_thread": self._thread is not None,
                "has_kernel": self._kernel is not None,
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="semantic_kernel",
                success=True,
                details={
                    "agent_id": agent_id,
                    "state_keys": list(state.keys()),
                    "num_messages": len(state.get("chat_history", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="semantic_kernel",
            source_version=SK_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(self, payload: StateWeavePayload, **kwargs) -> Any:
        """Import a StateWeavePayload into Semantic Kernel."""
        target_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            # If thread is available, deserialize into it
            if self._thread and hasattr(self._thread, "Deserialize"):
                self._thread.Deserialize(state_dict.get("thread_state", {}))

            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into SK agent '{target_id}' (from {payload.source_framework})"
            )

            return {
                "agent_id": target_id,
                "framework": "semantic_kernel",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import into SK agent '{target_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known SK agents."""
        agents = []
        if self._agent:
            name = getattr(self._agent, "name", "default")
            agents.append(
                AgentInfo(
                    agent_id=name,
                    agent_name=f"sk-{name}",
                    framework="semantic_kernel",
                    metadata={"source": "live_agent"},
                )
            )
        for agent_id in self._agents:
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"sk-{agent_id}",
                    framework="semantic_kernel",
                    metadata={"source": "local_store"},
                )
            )
        return agents

    def _extract_state(self) -> Dict[str, Any]:
        """Extract state from SK components."""
        state: Dict[str, Any] = {}

        # Serialize thread
        if self._thread:
            if hasattr(self._thread, "Serialize"):
                state["thread_state"] = self._thread.Serialize()
            elif hasattr(self._thread, "serialize"):
                state["thread_state"] = self._thread.serialize()

        # Extract chat history
        if self._chat_history:
            state["chat_history"] = []
            if hasattr(self._chat_history, "messages"):
                for msg in self._chat_history.messages:
                    msg_dict: Dict[str, Any] = {}
                    if hasattr(msg, "role"):
                        msg_dict["role"] = str(
                            msg.role.value if hasattr(msg.role, "value") else msg.role
                        )
                    if hasattr(msg, "content"):
                        msg_dict["content"] = str(msg.content)
                    if hasattr(msg, "name"):
                        msg_dict["name"] = msg.name
                    if hasattr(msg, "metadata"):
                        msg_dict["metadata"] = dict(msg.metadata)
                    state["chat_history"].append(msg_dict)

        # Extract plugin/function info from kernel
        if self._kernel:
            if hasattr(self._kernel, "plugins"):
                state["plugins"] = []
                for plugin_name, plugin in self._kernel.plugins.items():
                    plugin_info: Dict[str, Any] = {"name": plugin_name}
                    if hasattr(plugin, "functions"):
                        plugin_info["functions"] = [
                            {"name": fn_name} for fn_name in plugin.functions
                        ]
                    state["plugins"].append(plugin_info)

        # Extract agent config
        if self._agent:
            state["agent_name"] = getattr(self._agent, "name", "unknown")
            state["instructions"] = getattr(self._agent, "instructions", "")

        return state

    def _translate_to_cognitive_state(self, state: Dict[str, Any]) -> CognitiveState:
        """Translate SK state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        tool_results: Dict[str, ToolResult] = {}

        # Chat history → conversation history
        if "chat_history" in state:
            for msg in state["chat_history"]:
                if isinstance(msg, dict):
                    role_str = msg.get("role", "user")
                    role = SK_ROLE_MAP.get(role_str, MessageRole.HUMAN)
                    messages.append(
                        Message(
                            role=role,
                            content=str(msg.get("content", "")),
                            name=msg.get("name"),
                            metadata=msg.get("metadata", {}),
                        )
                    )

        # Thread state → working memory
        if "thread_state" in state:
            working_memory["sk_thread_state"] = state["thread_state"]

        # Agent config
        if "instructions" in state:
            working_memory["sk_instructions"] = state["instructions"]

        # Plugins → tool results
        if "plugins" in state:
            for plugin in state["plugins"]:
                if isinstance(plugin, dict):
                    name = plugin.get("name", "unknown")
                    tool_results[f"plugin_{name}"] = ToolResult(
                        tool_name=name,
                        arguments={},
                        result={
                            "functions": plugin.get("functions", []),
                        },
                        success=True,
                    )

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            tool_results_cache=tool_results,
        )

    def _translate_from_cognitive_state(self, cognitive_state: CognitiveState) -> Dict[str, Any]:
        """Translate Universal Schema to SK state."""
        state: Dict[str, Any] = {}

        if cognitive_state.conversation_history:
            state["chat_history"] = []
            for msg in cognitive_state.conversation_history:
                role = UNIVERSAL_TO_SK_ROLE.get(msg.role, "user")
                state["chat_history"].append(
                    {
                        "role": role,
                        "content": msg.content,
                    }
                )

        if "sk_thread_state" in cognitive_state.working_memory:
            state["thread_state"] = cognitive_state.working_memory["sk_thread_state"]
        if "sk_instructions" in cognitive_state.working_memory:
            state["instructions"] = cognitive_state.working_memory["sk_instructions"]

        return state

    def _detect_non_portable(self, state: Dict[str, Any]) -> List[NonPortableWarning]:
        """Detect SK-specific non-portable elements."""
        warnings = []

        if "plugins" in state:
            warnings.append(
                NonPortableWarning(
                    field="plugins",
                    reason=(
                        "SK plugin registrations are framework-specific — "
                        "function implementations are not portable"
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=True,
                    recommendation=(
                        "Plugin metadata is preserved. Re-register plugins "
                        "in the target framework after import."
                    ),
                )
            )

        for key in SK_INTERNAL_KEYS:
            if key in state:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"SK internal '{key}' is non-portable",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=False,
                        recommendation="Stripped during export",
                    )
                )

        return warnings
