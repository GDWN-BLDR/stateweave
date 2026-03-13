"""
LlamaIndex Adapter — Translates LlamaIndex agent state ↔ Universal Schema.
=============================================================================
Maps LlamaIndex's serializable Context, Memory class, and Memory Blocks
(static, fact extraction, vector) to the StateWeave Universal Schema.

LlamaIndex stores state as:
  - Context object (workflow state, serializable to dict)
  - Memory class (short-term + long-term memory blocks)
  - Chat history (messages with roles)
  - External storage references (vector stores, SQL)
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

logger = logging.getLogger("stateweave.adapters.llamaindex")

LLAMAINDEX_TARGET_VERSION = "0.12.x"

# Role mapping: LlamaIndex ChatMessage roles → Universal Schema
LLAMAINDEX_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "human": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
    "chatbot": MessageRole.ASSISTANT,
}

UNIVERSAL_TO_LLAMAINDEX_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

# LlamaIndex internal fields that are non-portable
LLAMAINDEX_INTERNAL_KEYS = {
    "_vector_store_ref",
    "_index_struct",
    "_service_context",
    "_storage_context",
    "_llm_predictor",
    "_embed_model_ref",
}


class LlamaIndexAdapter(StateWeaveAdapter):
    """Adapter for LlamaIndex (llama-index>=0.11.0).

    Translates between LlamaIndex's Context + Memory system and the
    StateWeave Universal Schema.

    Supports:
      - Agent workflow Context (serializable state)
      - Memory class with short/long-term blocks
      - Chat message history
      - Static, Fact Extraction, and Vector memory blocks

    Usage:
        adapter = LlamaIndexAdapter(agent=my_agent)
        payload = adapter.export_state("my-agent")
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        memory: Optional[Any] = None,
        context: Optional[Any] = None,
    ):
        """Initialize the LlamaIndex adapter.

        Args:
            agent: A LlamaIndex agent instance.
            memory: A LlamaIndex Memory instance.
            context: A LlamaIndex Context instance.
        """
        self._agent = agent
        self._memory = memory
        self._context = context
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "llamaindex"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.COMMUNITY

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export LlamaIndex agent state to Universal Schema.

        Args:
            agent_id: Identifier for this agent.
            **kwargs: Additional options:
                - include_memory_blocks: bool (default True)
                - include_chat_history: bool (default True)

        Returns:
            StateWeavePayload with the agent's cognitive state.
        """
        include_memory = kwargs.get("include_memory_blocks", True)
        include_history = kwargs.get("include_chat_history", True)

        try:
            state = self._extract_state()
        except Exception as e:
            raise ExportError(f"Failed to get LlamaIndex state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(state, include_memory, include_history)
        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"llamaindex-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["llamaindex"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "agent_type": type(self._agent).__name__ if self._agent else "unknown",
                "has_memory": self._memory is not None,
                "has_context": self._context is not None,
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="llamaindex",
                success=True,
                details={
                    "agent_id": agent_id,
                    "state_keys": list(state.keys()),
                    "num_messages": len(state.get("chat_history", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="llamaindex",
            source_version=LLAMAINDEX_TARGET_VERSION,
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
        """Import a StateWeavePayload into LlamaIndex.

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

            if self._memory and hasattr(self._memory, "put"):
                # Restore chat messages into memory
                for msg_data in state_dict.get("chat_history", []):
                    self._memory.put(msg_data)
            if self._context and hasattr(self._context, "from_dict"):
                context_data = state_dict.get("context", {})
                if context_data:
                    self._context = type(self._context).from_dict(context_data)

            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into LlamaIndex agent '{target_id}' "
                f"(from {payload.source_framework})"
            )

            return {
                "agent_id": target_id,
                "framework": "llamaindex",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import into LlamaIndex agent '{target_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known LlamaIndex agents."""
        agents = []

        if self._agent:
            agents.append(
                AgentInfo(
                    agent_id="default",
                    agent_name=f"llamaindex-{type(self._agent).__name__}",
                    framework="llamaindex",
                    metadata={"source": "live_agent"},
                )
            )

        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"llamaindex-{agent_id}",
                    framework="llamaindex",
                    metadata={"source": "local_store"},
                )
            )

        return agents

    def _extract_state(self) -> Dict[str, Any]:
        """Extract state from LlamaIndex agent, memory, or context."""
        state: Dict[str, Any] = {}

        # Extract from context (serializable workflow state)
        if self._context:
            if hasattr(self._context, "to_dict"):
                state["context"] = self._context.to_dict()
            elif isinstance(self._context, dict):
                state["context"] = self._context

        # Extract from memory
        if self._memory:
            if hasattr(self._memory, "get_all"):
                state["chat_history"] = self._memory.get_all()
            elif hasattr(self._memory, "chat_store"):
                chat_store = self._memory.chat_store
                if hasattr(chat_store, "store"):
                    state["chat_history"] = []
                    for key, messages in chat_store.store.items():
                        for msg in messages:
                            if hasattr(msg, "dict"):
                                state["chat_history"].append(msg.dict())
                            elif isinstance(msg, dict):
                                state["chat_history"].append(msg)

            # Extract memory blocks
            if hasattr(self._memory, "memory_blocks"):
                state["memory_blocks"] = {}
                for block in self._memory.memory_blocks:
                    block_data = {}
                    if hasattr(block, "get"):
                        block_data["content"] = block.get()
                    if hasattr(block, "name"):
                        block_name = block.name
                    else:
                        block_name = type(block).__name__
                    state["memory_blocks"][block_name] = block_data

        # Extract from agent
        if self._agent:
            if hasattr(self._agent, "chat_history"):
                history = self._agent.chat_history
                if history and "chat_history" not in state:
                    state["chat_history"] = []
                    for msg in history:
                        if hasattr(msg, "dict"):
                            state["chat_history"].append(msg.dict())
                        elif isinstance(msg, dict):
                            state["chat_history"].append(msg)

            if hasattr(self._agent, "tools"):
                state["tools"] = [
                    {"name": t.metadata.name, "description": t.metadata.description}
                    for t in self._agent.tools
                    if hasattr(t, "metadata")
                ]

        return state

    def _translate_to_cognitive_state(
        self,
        state: Dict[str, Any],
        include_memory: bool = True,
        include_history: bool = True,
    ) -> CognitiveState:
        """Translate LlamaIndex state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        long_term_memory: Dict[str, Any] = {}
        tool_results: Dict[str, ToolResult] = {}

        # Extract chat history
        if include_history and "chat_history" in state:
            for msg in state["chat_history"]:
                if isinstance(msg, dict):
                    role_str = msg.get("role", "user")
                    role = LLAMAINDEX_ROLE_MAP.get(role_str, MessageRole.HUMAN)
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

        # Extract memory blocks
        if include_memory and "memory_blocks" in state:
            blocks = state["memory_blocks"]
            for block_name, block_data in blocks.items():
                if "fact" in block_name.lower():
                    long_term_memory[f"facts_{block_name}"] = block_data
                elif "vector" in block_name.lower():
                    long_term_memory[f"vectors_{block_name}"] = block_data
                else:
                    working_memory[f"block_{block_name}"] = block_data

        # Extract context into working memory
        if "context" in state:
            working_memory["llamaindex_context"] = state["context"]

        # Extract tools into tool results cache
        if "tools" in state:
            for tool in state["tools"]:
                if isinstance(tool, dict):
                    tool_name = tool.get("name", "unknown")
                    tool_results[tool_name] = ToolResult(
                        tool_name=tool_name,
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

    def _translate_from_cognitive_state(
        self,
        cognitive_state: CognitiveState,
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to LlamaIndex state."""
        state: Dict[str, Any] = {}

        # Restore chat history
        if cognitive_state.conversation_history:
            state["chat_history"] = []
            for msg in cognitive_state.conversation_history:
                role = UNIVERSAL_TO_LLAMAINDEX_ROLE.get(msg.role, "user")
                state["chat_history"].append(
                    {
                        "role": role,
                        "content": msg.content,
                        **({"name": msg.name} if msg.name else {}),
                    }
                )

        # Restore context from working memory
        if "llamaindex_context" in cognitive_state.working_memory:
            state["context"] = cognitive_state.working_memory["llamaindex_context"]

        # Restore memory blocks
        memory_blocks: Dict[str, Any] = {}
        for key, value in cognitive_state.working_memory.items():
            if key.startswith("block_"):
                block_name = key[len("block_") :]
                memory_blocks[block_name] = value
        for key, value in cognitive_state.long_term_memory.items():
            if key.startswith("facts_") or key.startswith("vectors_"):
                prefix, block_name = key.split("_", 1)
                memory_blocks[block_name] = value
        if memory_blocks:
            state["memory_blocks"] = memory_blocks

        return state

    def _detect_non_portable(
        self,
        state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect LlamaIndex-specific non-portable elements."""
        warnings = []

        # Vector store references are non-portable
        if "memory_blocks" in state:
            for block_name, block_data in state["memory_blocks"].items():
                if "vector" in block_name.lower():
                    warnings.append(
                        NonPortableWarning(
                            field=f"memory_blocks.{block_name}",
                            reason=(
                                "Vector memory block contains embedding "
                                "references that are store-specific"
                            ),
                            severity=NonPortableWarningSeverity.WARN,
                            data_loss=True,
                            recommendation=(
                                "Re-embed documents in the target framework's "
                                "vector store after import"
                            ),
                        )
                    )

        # Tool metadata (no actual callable)
        if "tools" in state:
            warnings.append(
                NonPortableWarning(
                    field="tools",
                    reason=(
                        "Tool definitions contain metadata only — callable "
                        "implementations are framework-specific"
                    ),
                    severity=NonPortableWarningSeverity.INFO,
                    data_loss=False,
                    recommendation=("Re-register tools in the target framework after import"),
                )
            )

        # Service context / LLM predictor references
        for key in LLAMAINDEX_INTERNAL_KEYS:
            if key in state:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"LlamaIndex internal reference '{key}' is non-portable",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=False,
                        recommendation="This field will be stripped during export",
                    )
                )

        return warnings
