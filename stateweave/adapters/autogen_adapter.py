"""
AutoGen Adapter — Translates AutoGen ConversableAgent state ↔ Universal Schema.
==================================================================================
AutoGen uses ConversableAgent with chat_messages dict and optional
save_state/load_state. The adapter handles both structured and
unstructured state, with graceful fallbacks for partial states.
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

logger = logging.getLogger("stateweave.adapters.autogen")

AUTOGEN_TARGET_VERSION = "0.4.x"

# AutoGen internal fields that shouldn't transfer
AUTOGEN_INTERNAL_FIELDS = {
    "_oai_system_message",  # Raw OAI format system message
    "_code_execution_config",  # Code execution sandbox config
    "_is_termination_msg",  # Termination function reference
    "_max_consecutive_auto_reply",
    "_human_input_mode",  # NEVER/ALWAYS/TERMINATE
    "_function_map",  # Registered function references
    "client",  # LLM client instance
    "_reply_func_list",  # Reply function chain
}

# AutoGen message role mapping
AUTOGEN_ROLE_MAP: Dict[str, MessageRole] = {
    "user": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "function": MessageRole.FUNCTION,
    "tool": MessageRole.TOOL,
}

UNIVERSAL_TO_AUTOGEN_ROLE: Dict[MessageRole, str] = {
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.FUNCTION: "function",
    MessageRole.TOOL: "tool",
}


class AutoGenAdapter(StateWeaveAdapter):
    """Adapter for AutoGen (pyautogen>=0.4).

    AutoGen organizes agents as ConversableAgent instances that
    maintain chat_messages dicts tracking conversations with other
    agents. This adapter captures:

    - Multi-agent conversation histories (grouped by counterpart)
    - System messages and agent descriptions
    - Function/tool invocation results
    - Group chat topology (non-portable)

    Usage:
        adapter = AutoGenAdapter()
        adapter.register_agent("my-agent", {
            "name": "research_agent",
            "system_message": "You are a research assistant...",
            "chat_messages": {
                "user_proxy": [...],
                "coder": [...],
            },
        })
        payload = adapter.export_state("my-agent")

    Known issue (from research): AutoGen has known issues with state
    corruption on interruption. This adapter validates state integrity
    and emits warnings for partial/corrupted states.
    """

    def __init__(self):
        """Initialize the AutoGen adapter."""
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "autogen"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_1

    def register_agent(
        self,
        agent_id: str,
        state: Dict[str, Any],
    ) -> None:
        """Register an AutoGen agent's state for export.

        Args:
            agent_id: Unique identifier for the agent.
            state: Dict containing agent state:
                - name: str — agent name
                - system_message: str — system prompt
                - description: str — agent description
                - chat_messages: Dict[str, List[Dict]] — messages by counterpart
                - human_input_mode: str — NEVER/ALWAYS/TERMINATE
                - code_execution_config: Dict — sandbox config
                - function_results: Dict — cached function call results
                - group_chat: Dict — group chat config (if applicable)
        """
        # Validate state integrity
        if "chat_messages" in state:
            for counterpart, messages in state["chat_messages"].items():
                if not isinstance(messages, list):
                    logger.warning(
                        f"AutoGen agent '{agent_id}': chat_messages['{counterpart}'] "
                        f"is not a list — possible state corruption"
                    )

        self._agents[agent_id] = {
            **state,
            "_registered_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Registered AutoGen agent state: {agent_id}")

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export AutoGen agent state to Universal Schema.

        Args:
            agent_id: The agent identifier.

        Returns:
            StateWeavePayload with the agent's cognitive state.
        """
        if agent_id not in self._agents:
            raise ExportError(
                f"AutoGen agent '{agent_id}' not registered. Call register_agent() first."
            )

        raw_state = self._agents[agent_id]

        # Translate to cognitive state
        cognitive_state = self._translate_to_cognitive_state(raw_state)

        # Detect non-portable elements
        warnings = self._detect_non_portable(raw_state)

        # Check for state corruption
        corruption_warnings = self._check_state_integrity(raw_state)
        warnings.extend(corruption_warnings)

        # Build metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=raw_state.get("name", f"autogen-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["autogen"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "human_input_mode": raw_state.get("human_input_mode", "NEVER"),
                "has_code_execution": "code_execution_config" in raw_state,
                "counterpart_count": len(raw_state.get("chat_messages", {})),
            },
        )

        # Build audit trail
        total_messages = sum(
            len(msgs)
            for msgs in raw_state.get("chat_messages", {}).values()
            if isinstance(msgs, list)
        )
        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="autogen",
                success=True,
                details={
                    "agent_id": agent_id,
                    "agent_name": raw_state.get("name", "unknown"),
                    "total_messages": total_messages,
                    "counterparts": list(raw_state.get("chat_messages", {}).keys()),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="autogen",
            source_version=AUTOGEN_TARGET_VERSION,
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
        """Import a StateWeavePayload into AutoGen format.

        Translates Universal Schema back to AutoGen-compatible
        ConversableAgent state.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - agent_id: str — override agent ID
                - counterpart_name: str — default counterpart for flat history

        Returns:
            Dict with agent_id and state summary.
        """
        agent_id = kwargs.get("agent_id", payload.metadata.agent_id)
        default_counterpart = kwargs.get("counterpart_name", "user_proxy")

        try:
            state_dict = self._translate_from_cognitive_state(
                payload.cognitive_state,
                default_counterpart=default_counterpart,
            )
            state_dict["_imported_from"] = payload.source_framework
            state_dict["_import_timestamp"] = datetime.utcnow().isoformat()

            self._agents[agent_id] = state_dict

            logger.info(
                f"Imported state into AutoGen agent '{agent_id}' (from {payload.source_framework})"
            )

            return {
                "agent_id": agent_id,
                "framework": "autogen",
                "agent_name": state_dict.get("name", "unknown"),
                "message_count": sum(
                    len(msgs)
                    for msgs in state_dict.get("chat_messages", {}).values()
                    if isinstance(msgs, list)
                ),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(
                f"Failed to import state into AutoGen agent '{agent_id}': {e}"
            ) from e

    def list_agents(self) -> List[AgentInfo]:
        """List all registered AutoGen agents."""
        agents = []
        for agent_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=state.get("name", f"autogen-{agent_id}"),
                    framework="autogen",
                    last_active=datetime.fromisoformat(state["_registered_at"])
                    if "_registered_at" in state
                    else None,
                    metadata={
                        "human_input_mode": state.get("human_input_mode", "NEVER"),
                        "counterparts": list(state.get("chat_messages", {}).keys()),
                    },
                )
            )
        return agents

    def _translate_to_cognitive_state(
        self,
        raw_state: Dict[str, Any],
    ) -> CognitiveState:
        """Translate AutoGen agent state to Universal Schema CognitiveState."""
        messages = []
        working_memory = {}
        tool_results = {}

        # System message goes to working memory
        if "system_message" in raw_state:
            working_memory["system_message"] = raw_state["system_message"]
        if "description" in raw_state:
            working_memory["agent_description"] = raw_state["description"]
        if "name" in raw_state:
            working_memory["agent_name"] = raw_state["name"]

        # Flatten chat_messages from all counterparts into a single history
        # Preserve counterpart context via message.name field
        chat_messages = raw_state.get("chat_messages", {})
        all_messages = []
        for counterpart, msgs in chat_messages.items():
            if not isinstance(msgs, list):
                continue
            for msg in msgs:
                all_messages.append((counterpart, msg))

        # Sort by any available ordering (position in original lists)
        for counterpart, msg in all_messages:
            role_str = msg.get("role", "assistant")
            role = AUTOGEN_ROLE_MAP.get(role_str, MessageRole.ASSISTANT)

            content = msg.get("content", "")
            if content is None:
                content = ""

            translated = Message(
                role=role,
                content=str(content),
                name=counterpart,
                metadata={
                    "counterpart": counterpart,
                    **{
                        k: v
                        for k, v in msg.items()
                        if k not in ("role", "content", "name") and not isinstance(v, (type(None),))
                    },
                },
            )

            # Handle function/tool calls in the message
            if "function_call" in msg:
                translated.metadata["function_call"] = msg["function_call"]
            if "tool_calls" in msg:
                translated.metadata["tool_calls"] = msg["tool_calls"]

            messages.append(translated)

        # Function results
        for key, value in raw_state.get("function_results", {}).items():
            tool_results[key] = ToolResult(
                tool_name=key,
                result=value,
                success=True,
            )

        # Group chat config goes to working memory (for reference)
        if "group_chat" in raw_state:
            working_memory["_source_group_chat"] = raw_state["group_chat"]

        # Human input mode
        if "human_input_mode" in raw_state:
            working_memory["_source_human_input_mode"] = raw_state["human_input_mode"]

        # Store counterpart list for reconstruction during import
        if chat_messages:
            working_memory["_counterparts"] = list(chat_messages.keys())

        # Any other custom state
        skip_keys = {
            "name",
            "system_message",
            "description",
            "chat_messages",
            "human_input_mode",
            "code_execution_config",
            "function_results",
            "group_chat",
            "_registered_at",
            "_imported_from",
            "_import_timestamp",
        } | AUTOGEN_INTERNAL_FIELDS
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
        default_counterpart: str = "user_proxy",
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to AutoGen agent state."""
        state: Dict[str, Any] = {}

        wm = dict(cognitive_state.working_memory)

        # Restore system message
        if "system_message" in wm:
            state["system_message"] = wm.pop("system_message")
        if "agent_description" in wm:
            state["description"] = wm.pop("agent_description")
        if "agent_name" in wm:
            state["name"] = wm.pop("agent_name")

        # Reconstruct chat_messages grouped by counterpart
        counterparts = wm.pop("_counterparts", [default_counterpart])
        chat_messages: Dict[str, List[Dict]] = {cp: [] for cp in counterparts}

        for msg in cognitive_state.conversation_history:
            counterpart = (
                msg.metadata.get("counterpart", msg.name) if msg.metadata else msg.name
            ) or default_counterpart

            autogen_role = UNIVERSAL_TO_AUTOGEN_ROLE.get(msg.role, "assistant")
            autogen_msg: Dict[str, Any] = {
                "role": autogen_role,
                "content": msg.content,
            }

            # Restore function_call and tool_calls if present
            if msg.metadata:
                if "function_call" in msg.metadata:
                    autogen_msg["function_call"] = msg.metadata["function_call"]
                if "tool_calls" in msg.metadata:
                    autogen_msg["tool_calls"] = msg.metadata["tool_calls"]

            if counterpart not in chat_messages:
                chat_messages[counterpart] = []
            chat_messages[counterpart].append(autogen_msg)

        state["chat_messages"] = chat_messages

        # Restore function results
        if cognitive_state.tool_results_cache:
            function_results = {}
            for key, tr in cognitive_state.tool_results_cache.items():
                function_results[key] = tr.result if isinstance(tr, ToolResult) else tr
            state["function_results"] = function_results

        # Restore group chat config
        if "_source_group_chat" in wm:
            state["group_chat"] = wm.pop("_source_group_chat")
        if "_source_human_input_mode" in wm:
            state["human_input_mode"] = wm.pop("_source_human_input_mode")

        # Remaining working memory
        for key, value in wm.items():
            if not key.startswith("_"):
                state[key] = value

        return state

    def _detect_non_portable(
        self,
        raw_state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect AutoGen-specific non-portable elements."""
        warnings = []

        # Group chat topology
        if "group_chat" in raw_state:
            warnings.append(
                NonPortableWarning(
                    field="state.group_chat",
                    reason=(
                        "AutoGen group chat topology (speaker selection method, "
                        "allowed transitions) is framework-specific"
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=False,
                    recommendation=(
                        "Group chat config stored in working_memory for reference "
                        "but cannot be enforced in target framework"
                    ),
                )
            )

        # Code execution config
        if "code_execution_config" in raw_state:
            warnings.append(
                NonPortableWarning(
                    field="state.code_execution_config",
                    reason="Code execution sandbox configuration is environment-specific",
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=True,
                    recommendation="Re-configure code execution in target framework",
                )
            )

        # Human input mode
        if "human_input_mode" in raw_state:
            mode = raw_state["human_input_mode"]
            if mode != "NEVER":
                warnings.append(
                    NonPortableWarning(
                        field="state.human_input_mode",
                        reason=(
                            f"AutoGen human input mode '{mode}' is framework-specific "
                            f"and requires manual configuration in target"
                        ),
                        severity=NonPortableWarningSeverity.INFO,
                        data_loss=False,
                    )
                )

        # Internal fields
        for key in raw_state:
            if key in AUTOGEN_INTERNAL_FIELDS:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"AutoGen internal field '{key}' cannot transfer",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=True if "config" in key else False,
                    )
                )

        return warnings

    def _check_state_integrity(
        self,
        raw_state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Check for AutoGen state corruption (known issue).

        AutoGen can corrupt state on interruption. This checks for
        common corruption patterns.
        """
        warnings = []

        chat_messages = raw_state.get("chat_messages", {})
        for counterpart, msgs in chat_messages.items():
            if not isinstance(msgs, list):
                warnings.append(
                    NonPortableWarning(
                        field=f"state.chat_messages.{counterpart}",
                        reason=(
                            f"Expected list of messages, got {type(msgs).__name__}. "
                            f"Possible state corruption from interrupted execution."
                        ),
                        severity=NonPortableWarningSeverity.CRITICAL,
                        data_loss=True,
                        recommendation=(
                            "This conversation history may be corrupted. "
                            "Verify agent behavior after import."
                        ),
                    )
                )
                continue

            # Check for None content (corruption indicator)
            for i, msg in enumerate(msgs):
                if isinstance(msg, dict) and msg.get("content") is None:
                    if "function_call" not in msg and "tool_calls" not in msg:
                        warnings.append(
                            NonPortableWarning(
                                field=f"state.chat_messages.{counterpart}[{i}]",
                                reason="Message has None content without function/tool call",
                                severity=NonPortableWarningSeverity.WARN,
                                data_loss=False,
                                recommendation="Possible AutoGen state corruption",
                            )
                        )

        return warnings
