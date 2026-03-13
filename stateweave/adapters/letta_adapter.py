"""
Letta Adapter — Translates Letta/MemGPT agent state ↔ Universal Schema.
==========================================================================
Maps Letta's OS-like layered memory architecture (core memory blocks,
recall memory, archival memory) to the StateWeave Universal Schema.

Letta stores state as:
  - Core Memory: always-in-context memory blocks (label, value, limit)
  - Recall Memory: searchable event history database
  - Archival Memory: long-term read-write datastore
  - Agent configuration: system prompt, persona, tools
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

logger = logging.getLogger("stateweave.adapters.letta")

LETTA_TARGET_VERSION = "0.6.x"

LETTA_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
    "function": MessageRole.FUNCTION,
    "inner_thoughts": MessageRole.ASSISTANT,
}

UNIVERSAL_TO_LETTA_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
    MessageRole.FUNCTION: "function",
}

LETTA_INTERNAL_KEYS = {
    "_agent_id_internal",
    "_llm_config_ref",
    "_embedding_config_ref",
    "_persistence_manager_ref",
    "_client_ref",
}


class LettaAdapter(StateWeaveAdapter):
    """Adapter for Letta/MemGPT (letta>=0.5.0).

    Translates between Letta's OS-like layered memory system and the
    StateWeave Universal Schema.

    Supports:
      - Core memory blocks (persona, human, custom blocks)
      - Recall memory (conversation history)
      - Archival memory (long-term knowledge store)
      - Agent configuration and tools

    Usage:
        adapter = LettaAdapter(client=letta_client, agent_id="agent-123")
        payload = adapter.export_state("agent-123")
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        agent_state: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Letta adapter.

        Args:
            client: A Letta client instance (letta.Letta or REST client).
            agent_state: Pre-loaded agent state dict (alternative to client).
        """
        self._client = client
        self._agent_state = agent_state or {}
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "letta"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.COMMUNITY

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        """Export Letta agent state to Universal Schema."""
        include_archival = kwargs.get("include_archival", True)
        include_recall = kwargs.get("include_recall", True)

        try:
            state = self._extract_state(agent_id, include_archival, include_recall)
        except Exception as e:
            raise ExportError(f"Failed to get Letta state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(state)
        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", state.get("name", f"letta-{agent_id}")),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["letta", "memgpt"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "memory_model": "tiered_os",
                "has_core_memory": bool(state.get("core_memory")),
                "has_archival": bool(state.get("archival_memory")),
                "has_recall": bool(state.get("recall_memory")),
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="letta",
                success=True,
                details={
                    "agent_id": agent_id,
                    "core_blocks": len(state.get("core_memory", {})),
                    "recall_messages": len(state.get("recall_memory", [])),
                    "archival_passages": len(state.get("archival_memory", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="letta",
            source_version=LETTA_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(self, payload: StateWeavePayload, **kwargs) -> Any:
        """Import a StateWeavePayload into Letta."""
        target_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            if self._client:
                # Update core memory blocks via API
                for block_label, block_value in state_dict.get("core_memory", {}).items():
                    if hasattr(self._client, "update_block"):
                        self._client.update_block(
                            agent_id=target_id,
                            label=block_label,
                            value=block_value,
                        )

                # Insert archival memories
                for passage in state_dict.get("archival_memory", []):
                    if hasattr(self._client, "insert_archival_memory"):
                        self._client.insert_archival_memory(
                            agent_id=target_id,
                            memory=passage.get("text", str(passage)),
                        )

            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into Letta agent '{target_id}' (from {payload.source_framework})"
            )

            return {
                "agent_id": target_id,
                "framework": "letta",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import into Letta agent '{target_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known Letta agents."""
        agents = []

        if self._client and hasattr(self._client, "list_agents"):
            try:
                for agent in self._client.list_agents():
                    agents.append(
                        AgentInfo(
                            agent_id=getattr(agent, "id", str(agent)),
                            agent_name=getattr(agent, "name", f"letta-{agent}"),
                            framework="letta",
                            metadata={"source": "letta_api"},
                        )
                    )
            except Exception:
                pass

        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"letta-{agent_id}",
                    framework="letta",
                    metadata={"source": "local_store"},
                )
            )

        return agents

    def _extract_state(
        self,
        agent_id: str,
        include_archival: bool = True,
        include_recall: bool = True,
    ) -> Dict[str, Any]:
        """Extract state from Letta agent."""
        state: Dict[str, Any] = {}

        if self._agent_state:
            state = dict(self._agent_state)
        elif self._client:
            # Get agent via API
            if hasattr(self._client, "get_agent"):
                agent = self._client.get_agent(agent_id)
                if agent:
                    state["name"] = getattr(agent, "name", agent_id)
                    state["system"] = getattr(agent, "system", "")

            # Get core memory
            if hasattr(self._client, "get_core_memory"):
                core = self._client.get_core_memory(agent_id)
                if core:
                    state["core_memory"] = {}
                    if hasattr(core, "blocks"):
                        for block in core.blocks:
                            label = getattr(block, "label", "unknown")
                            value = getattr(block, "value", "")
                            state["core_memory"][label] = value
                    elif isinstance(core, dict):
                        state["core_memory"] = core

            # Get recall memory (conversation history)
            if include_recall and hasattr(self._client, "get_messages"):
                messages = self._client.get_messages(agent_id, limit=1000)
                if messages:
                    state["recall_memory"] = []
                    for msg in messages:
                        if hasattr(msg, "dict"):
                            state["recall_memory"].append(msg.dict())
                        elif hasattr(msg, "model_dump"):
                            state["recall_memory"].append(msg.model_dump())
                        elif isinstance(msg, dict):
                            state["recall_memory"].append(msg)

            # Get archival memory
            if include_archival and hasattr(self._client, "get_archival_memory"):
                archival = self._client.get_archival_memory(agent_id, limit=1000)
                if archival:
                    state["archival_memory"] = []
                    for passage in archival:
                        if hasattr(passage, "text"):
                            state["archival_memory"].append({"text": passage.text})
                        elif isinstance(passage, dict):
                            state["archival_memory"].append(passage)
                        else:
                            state["archival_memory"].append({"text": str(passage)})

            # Get tools
            if hasattr(self._client, "get_tools_for_agent"):
                tools = self._client.get_tools_for_agent(agent_id)
                if tools:
                    state["tools"] = [
                        {
                            "name": getattr(t, "name", str(t)),
                            "description": getattr(t, "description", ""),
                        }
                        for t in tools
                    ]

        return state

    def _translate_to_cognitive_state(self, state: Dict[str, Any]) -> CognitiveState:
        """Translate Letta state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        long_term_memory: Dict[str, Any] = {}
        tool_results: Dict[str, ToolResult] = {}
        episodic_memory: List[Dict[str, Any]] = []

        # Core memory → working memory
        if "core_memory" in state:
            for label, value in state["core_memory"].items():
                working_memory[f"letta_core_{label}"] = value

        # System prompt
        if "system" in state:
            working_memory["letta_system_prompt"] = state["system"]

        # Recall memory → conversation history
        if "recall_memory" in state:
            for msg in state["recall_memory"]:
                if isinstance(msg, dict):
                    role_str = msg.get("role", "user")
                    role = LETTA_ROLE_MAP.get(role_str, MessageRole.HUMAN)
                    content = msg.get("text", msg.get("content", ""))
                    if content:
                        messages.append(
                            Message(
                                role=role,
                                content=str(content),
                                metadata={
                                    k: v
                                    for k, v in msg.items()
                                    if k not in ("role", "text", "content")
                                },
                            )
                        )

        # Archival memory → long-term memory
        if "archival_memory" in state:
            long_term_memory["letta_archival"] = state["archival_memory"]
            # Also record as episodic memory for richer representation
            for passage in state["archival_memory"]:
                if isinstance(passage, dict):
                    episodic_memory.append(passage)

        # Tools
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
            episodic_memory=episodic_memory,
        )

    def _translate_from_cognitive_state(self, cognitive_state: CognitiveState) -> Dict[str, Any]:
        """Translate Universal Schema to Letta state."""
        state: Dict[str, Any] = {}

        # Restore core memory from working memory
        core_memory: Dict[str, str] = {}
        system_prompt = ""
        for key, value in cognitive_state.working_memory.items():
            if key.startswith("letta_core_"):
                label = key[len("letta_core_") :]
                core_memory[label] = str(value)
            elif key == "letta_system_prompt":
                system_prompt = str(value)
        if core_memory:
            state["core_memory"] = core_memory
        if system_prompt:
            state["system"] = system_prompt

        # Restore recall memory from conversation history
        if cognitive_state.conversation_history:
            state["recall_memory"] = []
            for msg in cognitive_state.conversation_history:
                role = UNIVERSAL_TO_LETTA_ROLE.get(msg.role, "user")
                state["recall_memory"].append(
                    {
                        "role": role,
                        "text": msg.content,
                    }
                )

        # Restore archival memory from long-term memory
        archival = cognitive_state.long_term_memory.get("letta_archival", [])
        if archival:
            state["archival_memory"] = archival

        return state

    def _detect_non_portable(self, state: Dict[str, Any]) -> List[NonPortableWarning]:
        """Detect Letta-specific non-portable elements."""
        warnings = []

        # Letta's context management (auto-summarization) is framework-specific
        if state.get("core_memory"):
            warnings.append(
                NonPortableWarning(
                    field="core_memory",
                    reason=(
                        "Letta core memory blocks use context-window-aware "
                        "sizing that is framework-specific"
                    ),
                    severity=NonPortableWarningSeverity.INFO,
                    data_loss=False,
                    recommendation=(
                        "Core memory content is preserved. Size limits will "
                        "need reconfiguration in the target framework."
                    ),
                )
            )

        # Archival memory embeddings
        if state.get("archival_memory"):
            warnings.append(
                NonPortableWarning(
                    field="archival_memory",
                    reason=(
                        "Archival memory passages may have associated "
                        "embeddings that are model-specific"
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=True,
                    recommendation=(
                        "Text content is preserved. Re-embed in the target "
                        "framework's vector store after import."
                    ),
                )
            )

        for key in LETTA_INTERNAL_KEYS:
            if key in state:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"Letta internal '{key}' is non-portable",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=False,
                        recommendation="Stripped during export",
                    )
                )

        return warnings
