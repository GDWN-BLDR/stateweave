"""
Haystack Adapter — Translates Haystack agent state ↔ Universal Schema.
=========================================================================
Maps Haystack's State object, agent memory (short/long-term), and
pipeline component state to the StateWeave Universal Schema.

Haystack stores state as:
  - State object (messages field + custom schema fields)
  - Short-term memory (conversation context)
  - Long-term memory (persistent knowledge via vector stores)
  - Pipeline component state and configurations
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

logger = logging.getLogger("stateweave.adapters.haystack")

HAYSTACK_TARGET_VERSION = "2.8.x"

HAYSTACK_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
}

UNIVERSAL_TO_HAYSTACK_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

HAYSTACK_INTERNAL_KEYS = {
    "_pipeline_ref",
    "_document_store_ref",
    "_embedding_model_ref",
    "_component_registry",
}


class HaystackAdapter(StateWeaveAdapter):
    """Adapter for Haystack (haystack-ai>=2.0.0).

    Translates between Haystack's State object and memory system and
    the StateWeave Universal Schema.

    Usage:
        adapter = HaystackAdapter(agent=my_agent)
        payload = adapter.export_state("my-agent")
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        state: Optional[Any] = None,
        memory: Optional[Any] = None,
    ):
        """Initialize the Haystack adapter.

        Args:
            agent: A Haystack agent instance.
            state: A Haystack State object.
            memory: A Haystack memory component.
        """
        self._agent = agent
        self._state = state
        self._memory = memory
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "haystack"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.COMMUNITY

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        """Export Haystack agent state to Universal Schema."""
        try:
            raw_state = self._extract_state()
        except Exception as e:
            raise ExportError(f"Failed to get Haystack state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(raw_state)
        warnings = self._detect_non_portable(raw_state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"haystack-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["haystack"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "agent_type": type(self._agent).__name__ if self._agent else "unknown",
                "has_state": self._state is not None,
                "has_memory": self._memory is not None,
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="haystack",
                success=True,
                details={
                    "agent_id": agent_id,
                    "state_keys": list(raw_state.keys()),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="haystack",
            source_version=HAYSTACK_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(self, payload: StateWeavePayload, **kwargs) -> Any:
        """Import a StateWeavePayload into Haystack."""
        target_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)
            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into Haystack agent '{target_id}' "
                f"(from {payload.source_framework})"
            )

            return {
                "agent_id": target_id,
                "framework": "haystack",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import into Haystack agent '{target_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known Haystack agents."""
        agents = []
        if self._agent:
            agents.append(
                AgentInfo(
                    agent_id="default",
                    agent_name=f"haystack-{type(self._agent).__name__}",
                    framework="haystack",
                    metadata={"source": "live_agent"},
                )
            )
        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"haystack-{agent_id}",
                    framework="haystack",
                    metadata={"source": "local_store"},
                )
            )
        return agents

    def _extract_state(self) -> Dict[str, Any]:
        """Extract state from Haystack components."""
        state: Dict[str, Any] = {}

        if self._state:
            if hasattr(self._state, "messages"):
                state["messages"] = []
                for msg in self._state.messages:
                    if isinstance(msg, dict):
                        state["messages"].append(msg)
                    elif hasattr(msg, "to_dict"):
                        state["messages"].append(msg.to_dict())
            if hasattr(self._state, "__dict__"):
                for k, v in self._state.__dict__.items():
                    if not k.startswith("_") and k != "messages":
                        if isinstance(v, (str, int, float, bool, list, dict)):
                            state[f"state_{k}"] = v

        if self._memory:
            if hasattr(self._memory, "get_memories"):
                state["long_term_memories"] = self._memory.get_memories()
            elif hasattr(self._memory, "run"):
                state["memory_component"] = type(self._memory).__name__

        if self._agent:
            if hasattr(self._agent, "tools"):
                state["tools"] = []
                for tool in self._agent.tools:
                    tool_info: Dict[str, Any] = {
                        "name": getattr(tool, "name", type(tool).__name__),
                    }
                    if hasattr(tool, "description"):
                        tool_info["description"] = tool.description
                    state["tools"].append(tool_info)

        return state

    def _translate_to_cognitive_state(self, state: Dict[str, Any]) -> CognitiveState:
        """Translate Haystack state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        long_term_memory: Dict[str, Any] = {}
        tool_results: Dict[str, ToolResult] = {}

        if "messages" in state:
            for msg in state["messages"]:
                if isinstance(msg, dict):
                    role_str = msg.get("role", "user")
                    role = HAYSTACK_ROLE_MAP.get(role_str, MessageRole.HUMAN)
                    messages.append(
                        Message(
                            role=role,
                            content=str(msg.get("content", "")),
                            name=msg.get("name"),
                            metadata={
                                k: v for k, v in msg.items() if k not in ("role", "content", "name")
                            },
                        )
                    )

        if "long_term_memories" in state:
            long_term_memory["haystack_memories"] = state["long_term_memories"]

        for key, value in state.items():
            if key.startswith("state_"):
                working_memory[key] = value

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

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            long_term_memory=long_term_memory,
            tool_results_cache=tool_results,
        )

    def _translate_from_cognitive_state(self, cognitive_state: CognitiveState) -> Dict[str, Any]:
        """Translate Universal Schema to Haystack state."""
        state: Dict[str, Any] = {}

        if cognitive_state.conversation_history:
            state["messages"] = []
            for msg in cognitive_state.conversation_history:
                role = UNIVERSAL_TO_HAYSTACK_ROLE.get(msg.role, "user")
                state["messages"].append(
                    {
                        "role": role,
                        "content": msg.content,
                    }
                )

        for key, value in cognitive_state.working_memory.items():
            if key.startswith("state_"):
                state[key] = value

        if cognitive_state.long_term_memory:
            state["long_term_memories"] = cognitive_state.long_term_memory.get(
                "haystack_memories", {}
            )

        return state

    def _detect_non_portable(self, state: Dict[str, Any]) -> List[NonPortableWarning]:
        """Detect Haystack-specific non-portable elements."""
        warnings = []

        if "memory_component" in state:
            warnings.append(
                NonPortableWarning(
                    field="memory_component",
                    reason=("Haystack memory component reference is infrastructure-specific"),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=False,
                    recommendation=(
                        "Memory data is exported. Reconfigure the memory component after import."
                    ),
                )
            )

        for key in HAYSTACK_INTERNAL_KEYS:
            if key in state:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"Haystack internal '{key}' is non-portable",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=False,
                        recommendation="Stripped during export",
                    )
                )

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
