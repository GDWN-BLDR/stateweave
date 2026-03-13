"""
CrewAI Adapter — Translates CrewAI agent/crew state ↔ Universal Schema.
=========================================================================
CrewAI organizes agents into crews with tasks. The adapter maps:
- Agent attributes (role, goal, backstory) → working_memory
- Task results and outputs → tool_results_cache
- Crew execution log → conversation_history
- Non-portable: crew topology, process type, delegation chains
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
    GoalNode,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)

logger = logging.getLogger("stateweave.adapters.crewai")

CREWAI_TARGET_VERSION = "0.86.x"

# CrewAI process types that affect execution but don't transfer
NON_PORTABLE_PROCESS_FIELDS = {
    "process_type",  # sequential vs hierarchical vs consensus
    "manager_llm",  # manager agent for hierarchical crews
    "manager_agent",  # manager agent instance
    "planning",  # planning mode config
    "memory_config",  # CrewAI-specific memory backend config
    "cache_handler",  # framework-specific cache
    "embedder",  # embedding model config
    "task_callback",  # Python callback functions
    "step_callback",  # Python callback functions
}


class CrewAIAdapter(StateWeaveAdapter):
    """Adapter for CrewAI (crewai>=0.70).

    CrewAI organizes AI agents into "crews" — coordinated teams that
    execute tasks in sequence or hierarchy. This adapter captures the
    cognitive state accumulated during crew execution:

    - Agent identities (role, goal, backstory, tools)
    - Task execution results and delegation chains
    - Conversation/interaction logs between agents
    - Working memory accumulated during execution

    Usage:
        adapter = CrewAIAdapter()
        adapter.register_crew("my-crew", {
            "agents": [...],
            "tasks": [...],
            "execution_log": [...],
        })
        payload = adapter.export_state("my-crew")
    """

    def __init__(self):
        """Initialize the CrewAI adapter."""
        self._crews: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "crewai"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_1

    def register_crew(
        self,
        crew_id: str,
        state: Dict[str, Any],
    ) -> None:
        """Register a CrewAI crew's state for export.

        Since CrewAI doesn't expose a persistent state store natively,
        the caller must capture and provide the crew state.

        Args:
            crew_id: Unique identifier for the crew.
            state: Dict containing crew state:
                - agents: List[Dict] — agent definitions (role, goal, backstory, tools)
                - tasks: List[Dict] — task definitions and results
                - execution_log: List[Dict] — crew execution interactions
                - process_type: str — "sequential", "hierarchical", or "consensus"
                - memory: Dict — any accumulated memory
                - context: Dict — shared crew context
        """
        self._crews[crew_id] = {
            **state,
            "_registered_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Registered CrewAI crew state: {crew_id}")

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export CrewAI crew state to Universal Schema.

        Args:
            agent_id: The crew identifier.

        Returns:
            StateWeavePayload with the crew's accumulated cognitive state.

        Raises:
            ExportError: If crew is not registered.
        """
        if agent_id not in self._crews:
            raise ExportError(
                f"CrewAI crew '{agent_id}' not registered. Call register_crew() first."
            )

        raw_state = self._crews[agent_id]

        # Translate to cognitive state
        cognitive_state = self._translate_to_cognitive_state(raw_state)

        # Detect non-portable elements
        warnings = self._detect_non_portable(raw_state)

        # Build metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"crewai-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["crewai"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "process_type": raw_state.get("process_type", "sequential"),
                "agent_count": len(raw_state.get("agents", [])),
                "task_count": len(raw_state.get("tasks", [])),
            },
        )

        # Build audit trail
        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="crewai",
                success=True,
                details={
                    "crew_id": agent_id,
                    "agents": len(raw_state.get("agents", [])),
                    "tasks": len(raw_state.get("tasks", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="crewai",
            source_version=CREWAI_TARGET_VERSION,
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
        """Import a StateWeavePayload into CrewAI format.

        Translates Universal Schema back to CrewAI-compatible crew state.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - crew_id: str — override crew ID

        Returns:
            Dict with crew_id and state summary.
        """
        crew_id = kwargs.get("crew_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)
            state_dict["_imported_from"] = payload.source_framework
            state_dict["_import_timestamp"] = datetime.utcnow().isoformat()

            self._crews[crew_id] = state_dict

            logger.info(
                f"Imported state into CrewAI crew '{crew_id}' (from {payload.source_framework})"
            )

            return {
                "crew_id": crew_id,
                "framework": "crewai",
                "agent_count": len(state_dict.get("agents", [])),
                "task_count": len(state_dict.get("tasks", [])),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import state into CrewAI crew '{crew_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all registered CrewAI crews."""
        agents = []
        for crew_id, state in self._crews.items():
            agents.append(
                AgentInfo(
                    agent_id=crew_id,
                    agent_name=f"crewai-{crew_id}",
                    framework="crewai",
                    last_active=datetime.fromisoformat(state["_registered_at"])
                    if "_registered_at" in state
                    else None,
                    metadata={
                        "agent_count": len(state.get("agents", [])),
                        "task_count": len(state.get("tasks", [])),
                        "process_type": state.get("process_type", "sequential"),
                    },
                )
            )
        return agents

    def _translate_to_cognitive_state(
        self,
        raw_state: Dict[str, Any],
    ) -> CognitiveState:
        """Translate CrewAI crew state to Universal Schema CognitiveState."""
        messages = []
        working_memory = {}
        tool_results = {}
        goal_tree = {}

        # Translate agents to working memory
        agents = raw_state.get("agents", [])
        if agents:
            agent_profiles = {}
            for i, agent in enumerate(agents):
                agent_key = agent.get("role", f"agent_{i}")
                agent_profiles[agent_key] = {
                    "role": agent.get("role", ""),
                    "goal": agent.get("goal", ""),
                    "backstory": agent.get("backstory", ""),
                    "tools": agent.get("tools", []),
                    "allow_delegation": agent.get("allow_delegation", False),
                    "verbose": agent.get("verbose", False),
                }
                # Map agent goals to goal tree
                goal_tree[f"agent_{i}_goal"] = GoalNode(
                    goal_id=f"agent_{i}_goal",
                    description=agent.get("goal", ""),
                    status="active",
                    metadata={"agent_role": agent.get("role", "")},
                )
            working_memory["agent_profiles"] = agent_profiles

        # Translate tasks to working memory + tool results
        tasks = raw_state.get("tasks", [])
        for i, task in enumerate(tasks):
            task.get("description", f"task_{i}")[:50]

            # Task results become tool results
            if "output" in task or "result" in task:
                tool_results[f"task_{i}"] = ToolResult(
                    tool_name=f"crewai_task_{i}",
                    arguments={"description": task.get("description", "")},
                    result=task.get("output", task.get("result")),
                    success=True,
                )

            # Task definitions go to working memory
            working_memory[f"task_{i}"] = {
                "description": task.get("description", ""),
                "expected_output": task.get("expected_output", ""),
                "agent": task.get("agent", ""),
                "context": task.get("context", []),
            }

        # Translate execution log to conversation history
        for entry in raw_state.get("execution_log", []):
            role_str = entry.get("role", entry.get("agent_role", "assistant"))
            role_map = {
                "user": MessageRole.HUMAN,
                "human": MessageRole.HUMAN,
                "assistant": MessageRole.ASSISTANT,
                "agent": MessageRole.ASSISTANT,
                "system": MessageRole.SYSTEM,
                "tool": MessageRole.TOOL,
            }
            messages.append(
                Message(
                    role=role_map.get(role_str, MessageRole.ASSISTANT),
                    content=str(entry.get("content", entry.get("output", ""))),
                    name=entry.get("agent_role", entry.get("agent", None)),
                    metadata={
                        k: v
                        for k, v in entry.items()
                        if k not in ("role", "agent_role", "content", "output", "agent")
                    },
                )
            )

        # Shared crew context
        if "context" in raw_state:
            working_memory["crew_context"] = raw_state["context"]
        if "memory" in raw_state:
            working_memory["crew_memory"] = raw_state["memory"]

        # Process type (for reference, even though it's non-portable)
        if "process_type" in raw_state:
            working_memory["_source_process_type"] = raw_state["process_type"]

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
        """Translate Universal Schema CognitiveState to CrewAI crew state."""
        state: Dict[str, Any] = {}

        wm = dict(cognitive_state.working_memory)

        # Reconstruct agents from working memory
        agent_profiles = wm.pop("agent_profiles", {})
        if agent_profiles:
            state["agents"] = [
                {
                    "role": profile.get("role", key),
                    "goal": profile.get("goal", ""),
                    "backstory": profile.get("backstory", ""),
                    "tools": profile.get("tools", []),
                    "allow_delegation": profile.get("allow_delegation", False),
                }
                for key, profile in agent_profiles.items()
            ]

        # Reconstruct tasks
        tasks = []
        task_keys = sorted([k for k in wm if k.startswith("task_")])
        for key in task_keys:
            task_data = wm.pop(key)
            if isinstance(task_data, dict):
                task_entry = {
                    "description": task_data.get("description", ""),
                    "expected_output": task_data.get("expected_output", ""),
                }
                # Add result from tool_results
                task_idx = key.replace("task_", "")
                tool_key = f"task_{task_idx}"
                if tool_key in cognitive_state.tool_results_cache:
                    tr = cognitive_state.tool_results_cache[tool_key]
                    task_entry["output"] = tr.result if isinstance(tr, ToolResult) else tr
                tasks.append(task_entry)
        if tasks:
            state["tasks"] = tasks

        # Reconstruct execution log from conversation history
        if cognitive_state.conversation_history:
            execution_log = []
            role_map = {
                MessageRole.HUMAN: "user",
                MessageRole.ASSISTANT: "agent",
                MessageRole.SYSTEM: "system",
                MessageRole.TOOL: "tool",
            }
            for msg in cognitive_state.conversation_history:
                execution_log.append(
                    {
                        "role": role_map.get(msg.role, "agent"),
                        "content": msg.content,
                        **({"agent_role": msg.name} if msg.name else {}),
                    }
                )
            state["execution_log"] = execution_log

        # Restore context and memory
        if "crew_context" in wm:
            state["context"] = wm.pop("crew_context")
        if "crew_memory" in wm:
            state["memory"] = wm.pop("crew_memory")
        if "_source_process_type" in wm:
            state["process_type"] = wm.pop("_source_process_type")

        # Remaining working memory
        for key, value in wm.items():
            if not key.startswith("_"):
                state[key] = value

        return state

    def _detect_non_portable(
        self,
        raw_state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect CrewAI-specific non-portable elements."""
        warnings = []

        # Process type is structural, not portable
        if "process_type" in raw_state:
            process_type = raw_state["process_type"]
            warnings.append(
                NonPortableWarning(
                    field="state.process_type",
                    reason=(
                        f"CrewAI process type '{process_type}' is framework-specific. "
                        f"Other frameworks don't have equivalent execution topologies."
                    ),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=False,
                    recommendation=(
                        "Process type will be stored in working_memory for reference "
                        "but cannot be enforced in the target framework."
                    ),
                )
            )

        # Delegation chains can't transfer
        for agent in raw_state.get("agents", []):
            if agent.get("allow_delegation"):
                warnings.append(
                    NonPortableWarning(
                        field=f"state.agents.{agent.get('role', 'unknown')}.allow_delegation",
                        reason="Delegation chains are CrewAI-specific execution patterns",
                        severity=NonPortableWarningSeverity.INFO,
                        data_loss=False,
                    )
                )

        # Check for non-portable fields (skip process_type — handled above)
        for key in raw_state:
            if key in NON_PORTABLE_PROCESS_FIELDS and key != "process_type":
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"CrewAI internal field '{key}' is framework-specific",
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=key in ("cache_handler", "task_callback", "step_callback"),
                    )
                )

        return warnings
