"""
StateWeave Adapter Base — ABC for all framework adapters.
===========================================================
[LAW 4] Every framework adapter MUST extend this ABC and implement
all required methods. No adapter may bypass the contract.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List

from stateweave.schema.v1 import AgentInfo, StateWeavePayload

logger = logging.getLogger("stateweave.adapters.base")


class AdapterTier(str, Enum):
    """Support tier for framework adapters.

    TIER_1: Guaranteed stability. Maintained by core team. Breaking changes
            in the target framework are tracked and patched promptly.
    TIER_2: Actively maintained. Core team monitors for breakage but
            patches may lag behind framework releases.
    COMMUNITY: Best-effort. Contributed by the community. May break if the
               target framework changes internal state representations.
    """

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    COMMUNITY = "community"


class AdapterError(Exception):
    """Base exception for adapter errors."""

    pass


class ExportError(AdapterError):
    """Raised when state export fails."""

    pass


class ImportError_(AdapterError):
    """Raised when state import fails.

    Named ImportError_ to avoid shadowing the builtin ImportError.
    """

    pass


class StateWeaveAdapter(ABC):
    """Abstract base class for all framework adapters.

    Every adapter translates between a framework's native state
    representation and the Universal Schema (StateWeavePayload).

    The SSOT Charter mandates:
    - All translations go TO/FROM the Universal Schema
    - No direct framework-to-framework translation
    - Non-portable state MUST be reported via non_portable_warnings[]

    Subclasses must implement:
        - framework_name: str property
        - export_state(agent_id, **kwargs) -> StateWeavePayload
        - import_state(payload, **kwargs) -> Any
        - list_agents() -> List[AgentInfo]
    """

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """The name of the framework this adapter supports.

        Must be a stable identifier (e.g., "langgraph", "mcp", "crewai").
        Used in StateWeavePayload.source_framework.
        """
        ...

    @property
    @abstractmethod
    def tier(self) -> AdapterTier:
        """The support tier for this adapter.

        Determines the stability guarantee and maintenance commitment.
        See AdapterTier enum for tier definitions.
        """
        ...

    @abstractmethod
    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export an agent's cognitive state to a StateWeavePayload.

        Args:
            agent_id: Identifier of the agent to export.
            **kwargs: Framework-specific export options.

        Returns:
            A fully populated StateWeavePayload with cognitive state,
            metadata, and non-portable warnings.

        Raises:
            ExportError: If export fails.
        """
        ...

    @abstractmethod
    def import_state(
        self,
        payload: StateWeavePayload,
        **kwargs,
    ) -> Any:
        """Import a StateWeavePayload into this framework.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Framework-specific import options.

        Returns:
            A framework-native agent reference (type varies by framework).

        Raises:
            ImportError_: If import fails.
        """
        ...

    @abstractmethod
    def list_agents(self) -> List[AgentInfo]:
        """List all agents available in this framework instance.

        Returns:
            List of AgentInfo summaries.
        """
        ...

    def validate_payload(self, payload: StateWeavePayload) -> bool:
        """Validate that a payload can be imported into this framework.

        Default implementation checks basic schema validity.
        Subclasses can override for framework-specific validation.

        Args:
            payload: The payload to validate.

        Returns:
            True if the payload is importable.
        """
        try:
            # Basic validation — payload has required fields
            if not payload.stateweave_version:
                return False
            if not payload.metadata.agent_id:
                return False
            return True
        except Exception:
            return False

    def _require_framework(self, has_flag: bool, framework_name: str) -> None:
        """Check that the target framework is installed, with a helpful error.

        Call this at the start of export_state/import_state to give users
        a clear, actionable error message instead of a confusing ImportError
        deep in the call stack.

        Args:
            has_flag: The HAS_<FRAMEWORK> boolean from the adapter module.
            framework_name: Human-readable framework name for the error.

        Raises:
            AdapterError: If the framework is not installed.
        """
        if not has_flag:
            pip_extra = self.framework_name.replace("-", "_")
            raise AdapterError(
                f"{framework_name} is not installed. "
                f"To use the {self.framework_name} adapter, install it with:\n\n"
                f'    pip install "stateweave[{pip_extra}]"\n\n'
                f"Or install {framework_name} directly:\n\n"
                f"    pip install {framework_name}"
            )

    def create_sample_payload(
        self,
        agent_id: str = "sample-agent",
        num_messages: int = 3,
    ) -> StateWeavePayload:
        """Create a realistic sample payload for this framework.

        Works without the actual framework installed. Useful for demos,
        testing, and the quickstart experience.

        Args:
            agent_id: Identifier for the sample agent.
            num_messages: Number of sample conversation messages to include.

        Returns:
            A populated StateWeavePayload that can be checkpointed,
            diffed, and rolled back without any framework dependency.
        """
        from datetime import datetime

        from stateweave.schema.v1 import (
            AgentMetadata,
            CognitiveState,
            GoalNode,
            Message,
            StateWeavePayload,
            ToolResult,
        )

        sample_messages = [
            Message(role="system", content="You are a helpful AI assistant."),
            Message(role="human", content="Analyze the Q4 sales data and find trends."),
            Message(
                role="assistant",
                content="I'll analyze the Q4 sales data. Let me start by looking at the monthly breakdown...",
            ),
            Message(role="human", content="Focus on the top 3 product categories."),
            Message(
                role="assistant",
                content="Here are the top 3 categories: Electronics (+15%), Home & Garden (+8%), Sports (-3%).",
            ),
        ][:num_messages]

        return StateWeavePayload(
            schema_version="1.0.0",
            stateweave_version="0.3.0",
            source_framework=self.framework_name,
            metadata=AgentMetadata(
                agent_id=agent_id,
                agent_name=f"Sample {self.framework_name.title()} Agent",
                created_at=datetime.utcnow().isoformat(),
                description=f"Sample agent created for {self.framework_name} demonstration",
            ),
            cognitive_state=CognitiveState(
                conversation_history=sample_messages,
                working_memory={
                    "current_task": "Analyze Q4 sales data",
                    "confidence": 0.85,
                    "tools_used": ["data_query", "chart_generator"],
                },
                goal_tree={
                    "primary": GoalNode(
                        goal_id="primary",
                        description="Provide actionable sales insights",
                        status="active",
                    ),
                },
                tool_results_cache={
                    "data_query": ToolResult(
                        tool_name="data_query",
                        arguments={"query": "SELECT * FROM sales WHERE quarter='Q4'"},
                        result={"rows": 1247, "categories": 12},
                        success=True,
                    ),
                },
            ),
        )
